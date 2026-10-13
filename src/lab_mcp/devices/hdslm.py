from concurrent.futures import Future, TimeoutError
import copy
from pathlib import Path
import queue
import threading
import time
from ..errors import LabError
from .vendor import load_vendor_module, require_windows_x64
from . import windows


def select_roles(configs,displays):
    selected={}
    for role,cfg in configs.items():
        if not cfg.enabled: selected[role]=None; continue
        if not cfg.serial or cfg.desktop_xy is None:
            raise LabError('unbound',f'{role} requires today\'s serial and desktop rectangle')
        matches=[d for d in displays if d.get('sn')==cfg.serial and cfg.name_contains.lower() in d.get('name','').lower()
            and (d['x'],d['y'])==cfg.desktop_xy and (d['width'],d['height'])==cfg.panel_wh]
        if len(matches)>1: raise LabError('ambiguous_binding',f'Multiple matches for {role}')
        selected[role]=dict(matches[0]) if matches else None
    indices=[d['index'] for d in selected.values() if d is not None]
    if len(indices)!=len(set(indices)): raise LabError('duplicate_binding','SLM roles must select distinct displays')
    return selected


def probe_displays(sdk_dir):
    require_windows_x64(); windows.enable_owner_dpi()
    sdk=load_vendor_module('lab_probe_hdslm',Path(sdk_dir)/'hdslm_sdk.py').SLMDisplay(str(sdk_dir),verbose=False)
    return sdk.list_displays()


class HDSLMOwner:
    def __init__(self,configs,sdk_dir,*,sdk_factory=None):
        self.configs=configs; self.sdk_dir=Path(sdk_dir); self.factory=sdk_factory
        self.queue=queue.Queue(); self.thread=None; self.ready=None; self.state_lock=threading.RLock()
        self.states={role:{'status':'disconnected' if cfg.enabled else 'unavailable'} for role,cfg in configs.items()}
        self.opened={}; self.handles={}; self.fatal=None

    def _call(self,command,*args):
        if self.thread is None:
            self.ready=Future(); self.thread=threading.Thread(target=self._worker,name='HDSLM-owner',daemon=True)
            self.thread.start(); self.ready.result(timeout=30)
        if self.fatal: raise LabError('slm_owner_error',self.fatal,stage=command)
        future=Future(); self.queue.put((command,args,future))
        try: return future.result(timeout=30)
        except TimeoutError:
            self.fatal='SDK owner timed out; restart required'
            raise LabError('uncertain',self.fatal,stage=command,hardware_submitted=True) from None

    def connect(self,roles): return self._call('connect',roles)
    def show(self,role,panel): return self._call('show',role,panel)
    def status(self):
        with self.state_lock: return copy.deepcopy(self.states)
    def disconnect(self,roles=None):
        if self.thread is None: return self.status()
        result=self._call('disconnect',roles)
        if roles is None:
            self.thread.join(timeout=5); self.thread=None
        return result

    def _health(self,role,sdk):
        display=self.opened[role]; cfg=self.configs[role]
        expected=(*cfg.desktop_xy,*cfg.panel_wh)
        rectangles=sdk.topology_rectangles if self.factory and hasattr(sdk,'topology_rectangles') else windows.monitor_rectangles()
        if expected not in rectangles: raise LabError('topology_changed','Display topology changed; stop and rebind')
        if self.factory:
            alive=sdk.window_alive(display['index'])
            result={'alive':alive,'hung':sdk.window_hung(display['index']),'unobscured':alive,'simulation':True}
        else: result=windows.inspect_projection_window(self.handles[role],expected)
        if not result['alive'] or result['hung'] or result.get('rect_mismatch'):
            raise LabError('window_invalid','Projection window closed, moved or hung')
        return result

    def _worker(self):
        sdk=None
        try:
            if self.factory: sdk=self.factory()
            else:
                require_windows_x64(); windows.enable_owner_dpi()
                sdk=load_vendor_module('lab_vendor_hdslm',self.sdk_dir/'hdslm_sdk.py').SLMDisplay(str(self.sdk_dir),verbose=False)
            displays=sdk.list_displays()
            self.ready.set_result(True)
            next_health=0
            while True:
                sdk.pump()
                try: command,args,future=self.queue.get(timeout=.01)
                except queue.Empty:
                    if time.monotonic()>next_health:
                        with self.state_lock:
                            for role in list(self.opened):
                                try: self.states[role]['window']=self._health(role,sdk)
                                except Exception as exc: self.states[role].update(status='error',error=str(exc))
                        next_health=time.monotonic()+.25
                    continue
                terminate=False
                try:
                    if command=='connect':
                        selected=select_roles({r:self.configs[r] for r in args[0]},displays)
                        for role,d in selected.items():
                            if d is None:
                                self.states[role]={'status':'unavailable'}; continue
                            if role in self.opened: continue
                            if any(x['index']==d['index'] for x in self.opened.values()): raise LabError('duplicate_binding','Display already owned')
                            self.opened[role]=d
                            sdk.open(d['index'],harden=False)
                            sdk.set_offset(d['index'],0,0)
                            sdk._check('SLM_ADD_PhaseEnabled',sdk.lib.SLM_ADD_PhaseEnabled(d['index'],False))
                            sdk.pump()
                            if not self.factory: self.handles[role]=windows.find_projection_window((d['x'],d['y'],d['width'],d['height']))
                            self.states[role]={'status':'connected','selected':d,'window':self._health(role,sdk)}
                        result=self.status()
                    elif command=='show':
                        role,panel=args
                        if role not in self.opened or self.states[role]['status']=='error': raise LabError('unavailable',f'{role} is not usable')
                        health=self._health(role,sdk)
                        if not health['unobscured']: raise LabError('window_occluded','Projection window is covered')
                        sdk.show_array(self.opened[role]['index'],panel.codes,bit_flags=1<<panel.metadata['bit_depth'])
                        sdk.pump()
                        result={**panel.metadata,'submitted_monotonic_ns':time.monotonic_ns(),'window':self._health(role,sdk)}
                        self.states[role].update(last=result)
                    elif command=='disconnect':
                        roles=args[0]
                        for role in list(self.opened) if roles is None else roles:
                            d=self.opened.pop(role,None)
                            if d is not None: sdk.close(d['index'])
                            self.states[role]={'status':'disconnected' if self.configs[role].enabled else 'unavailable'}
                        result=self.status(); terminate=roles is None
                    else: raise ValueError('Unknown owner command')
                    future.set_result(result)
                except Exception as exc: future.set_exception(exc)
                if terminate: break
        except BaseException as exc:
            self.fatal=str(exc)
            if not self.ready.done(): self.ready.set_exception(exc)
        finally:
            for role,d in list(self.opened.items()):
                try: sdk.close(d['index'])
                except Exception: pass
            self.opened.clear()
