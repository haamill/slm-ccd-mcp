import copy
import threading
import time
import uuid
import numpy as np
from .models import LoadRequest, CameraPatch, CaptureRequest, JointRequest, GratingSpec
from .errors import LabError
from .imaging.io import read_codes, read_phase_lut
from .imaging.panel import compose_panel
from .imaging.grating import add_phase_grating, make_amplitude_grating


class LabController:
    def __init__(self,config,slm,camera,assets,captures,journal):
        self.config=config; self.slm=slm; self.camera=camera; self.assets=assets; self.captures=captures; self.journal=journal
        self.operation_lock=threading.RLock(); self.state_lock=threading.RLock(); self.version=0
        self.bases={}; self.restores={}; self.closed=False; self.last_error=None
        self.uncertain_results={}

    def status(self):
        with self.state_lock:
            return {'mode':self.config.mode,'state_version':self.version,'slms':self.slm.status(),
                'ccd':self.camera.status(),'last_error':copy.deepcopy(self.last_error),
                'checked_monotonic_ns':time.monotonic_ns()}

    def operation_get(self,operation_id):
        if operation_id in self.uncertain_results: return copy.deepcopy(self.uncertain_results[operation_id]['result'])
        return self.journal.get(operation_id)

    def _require_slm(self,role):
        if role not in ('slm1','slm2') or self.slm.status()[role]['status']!='connected':
            raise LabError('unavailable',f'{role} is unavailable')

    def _prepare_load(self,request,*,grating=None,base_codes=None):
        self._require_slm(request.role)
        if request.bit_depth is None:
            request=request.model_copy(update={'bit_depth':self.config.slms[request.role].bit_depth})
        codes=read_codes(self.assets.resolve(request.source),packed_rgb=request.packed_rgb) if base_codes is None else base_codes.copy()
        spec=grating or GratingSpec()
        lut=read_phase_lut(self.assets.resolve(spec.lut_source),expected_codes=1<<request.bit_depth) if spec.mode=='lut' and spec.lut_source else None
        shown=add_phase_grating(codes,spec,lut=lut) if request.role=='slm2' else codes
        panel=compose_panel(shown,self.config.slms[request.role],request)
        panel.metadata['grating']=spec.model_dump(mode='json')
        return {'codes':codes,'request':request.model_copy(deep=True),'grating':spec.model_copy(deep=True),'panel':panel}

    def _capture_preflight(self,request,patch=None):
        self.camera.check_capture_ready()
        s=self.camera.settings()
        exposure=patch.exposure_us if patch and patch.exposure_us is not None else s['exposure_us']
        minimum=request.settle_s+(request.frames+request.discard_frames+1)*exposure/1e6
        if not minimum<=request.timeout_s<=self.config.capture_timeout_max_s:
            raise ValueError('Timeout outside capture budget')
        if request.roi_xywh:
            x,y,w,h=request.roi_xywh
            if x+w>s['sensor_wh'][0] or y+h>s['sensor_wh'][1]: raise ValueError('ROI exceeds sensor')
        return self.captures.prepare(request,tuple(s['sensor_wh']),s['effective_bits'])

    def _preflight(self,op,args):
        if op in ('lab_connect','lab_disconnect'):
            roles=args.get('roles')
            if roles is not None and (not isinstance(roles,list) or any(r not in ('slm1','slm2','ccd') for r in roles) or len(set(roles))!=len(roles)):
                raise ValueError('Invalid device roles')
            return {'roles':roles}
        if op=='slm_load_image': return self._prepare_load(LoadRequest.model_validate(args))
        if op in ('slm_set_offset','slm_set_grating','slm_restore'):
            role=args.get('role','slm2'); self._require_slm(role)
            if op=='slm_restore':
                if role not in self.restores: raise ValueError('No registered restore image')
                base=self.restores[role]
                return self._prepare_load(base['request'],grating=base['grating'],base_codes=base['codes'])
            if role not in self.bases: raise ValueError('Load an image before adjusting it')
            base=self.bases[role]; req=base['request'].model_copy(deep=True); spec=base['grating']
            if op=='slm_set_offset':
                if req.placement=='panel': raise ValueError('Panel input has no offset')
                req.offset_xy=(args['offset_x_px'],args['offset_y_px'])
            else:
                if role!='slm2': raise ValueError('Phase grating applies only to SLM2')
                spec=GratingSpec.model_validate({k:v for k,v in args.items() if k!='role'})
            return self._prepare_load(req,grating=spec,base_codes=base['codes'])
        if op=='slm_show_uniform':
            role=args['role']; self._require_slm(role)
            gray=args['gray']; bits=args.get('bit_depth')
            if bits is None: bits=self.config.slms[role].bit_depth
            if type(gray) is not int or bits not in (8,10) or not 0<=gray<1<<bits: raise ValueError('Invalid uniform code')
            w,h=self.config.slms[role].panel_wh
            source=self.assets.register_codes(np.full((h,w),gray,dtype=np.uint8 if bits==8 else np.uint16),'uniform')
            return self._prepare_load(LoadRequest(role=role,source='asset:'+source['asset_id'],bit_depth=bits,placement='panel'))
        if op=='slm_make_amplitude_grating':
            return {'codes':make_amplitude_grating(**args)}
        if op=='ccd_set_settings':
            patch=CameraPatch.model_validate(args); self.camera.validate_patch(patch); return {'patch':patch}
        if op=='ccd_capture':
            request=CaptureRequest.model_validate(args); return {'capture':request,'writer':self._capture_preflight(request)}
        if op=='lab_load_and_capture':
            joint=JointRequest.model_validate(args)
            loads=[self._prepare_load(req) for req in joint.loads]
            if joint.camera_patch: self.camera.validate_patch(joint.camera_patch)
            writer=self._capture_preflight(joint.capture,joint.camera_patch)
            return {'loads':loads,'patch':joint.camera_patch,'capture':joint.capture,'writer':writer}
        raise ValueError('Unknown control operation')

    def execute(self,op,args,*,operation_id=None,expected_version=None):
        ident=operation_id or str(uuid.uuid4())
        params={'op':op,'args':args,'expected_version':expected_version}
        with self.operation_lock:
            if self.closed: raise LabError('closed','Controller has been closed')
            if ident in self.uncertain_results:
                cached=self.uncertain_results[ident]
                if cached['params']!=params: raise ValueError('Operation ID reused with different parameters')
                return copy.deepcopy(cached['result'])
            try: existing=self.journal.get(ident)
            except ValueError: existing=None
            if existing:
                record=self.journal.begin(ident,params)
                return record['result'] if record['result'] is not None else record
            if expected_version is not None and expected_version!=self.version:
                raise LabError('version_conflict','State changed since requested version')
            prepared=self._preflight(op,args)
            self.journal.begin(ident,params)
            submitted=False; stage='prepared'; advanced=False
            def mark(name,hardware=False):
                nonlocal stage,submitted
                if stage!='prepared': self.journal.complete_stage(ident,stage)
                stage=name; submitted=submitted or hardware
                self.journal.stage(ident,name,hardware_submitted=submitted)
            try:
                payload={}
                if op=='lab_connect':
                    roles=prepared['roles'] or [r for r,c in self.config.slms.items() if c.enabled]+['ccd']
                    mark('connect',True)
                    slm_roles=[r for r in roles if r!='ccd']
                    if slm_roles: payload['slms']=self.slm.connect(slm_roles)
                    if 'ccd' in roles: payload['ccd']=self.camera.connect()
                    for role in slm_roles:
                        restore=self.config.slms[role].restore_source
                        if restore and self.slm.status()[role]['status']=='connected':
                            req=LoadRequest(role=role,source=restore,bit_depth=self.config.slms[role].bit_depth)
                            self.restores[role]=self._prepare_load(req)
                elif op=='lab_disconnect':
                    mark('disconnect',True); payload=self._disconnect(prepared['roles'])
                elif op.startswith('slm_') and op!='slm_make_amplitude_grating':
                    role=prepared['request'].role; mark(role+'.show',True)
                    payload=self._show(prepared)
                elif op=='slm_make_amplitude_grating':
                    mark('asset.create'); payload=self.assets.register_codes(prepared['codes'],'amplitude grating')
                elif op=='ccd_set_settings':
                    mark('camera.settings',True); payload=self.camera.apply_settings(prepared['patch'])
                else:
                    if prepared.get('patch'):
                        mark('camera.settings',True); self.camera.apply_settings(prepared['patch'])
                    boundary=time.monotonic_ns()
                    for load in sorted(prepared.get('loads',[]),key=lambda item:0 if item['request'].role=='slm2' else 1):
                        mark(load['request'].role+'.show',True); response=self._show(load)
                        boundary=response['submitted_monotonic_ns']
                    mark('camera.capture',True)
                    metadata=self.camera.capture(prepared['capture'],boundary,prepared['writer'].write_frame)
                    mark('capture.save'); payload=prepared['writer'].finish({**metadata,'state_before':self.status()})
                with self.state_lock: self.version+=1; advanced=True
                result={'operation_id':ident,'status':'succeeded','state_version':self.version,'result':payload}
                self.journal.complete_stage(ident,stage)
                self.journal.finish(ident,result)
                return result
            except Exception as exc:
                error=exc.to_dict() if isinstance(exc,LabError) else LabError('operation_failed',str(exc)).to_dict()
                error.update(stage=stage,hardware_submitted=submitted)
                if 'writer' in prepared:
                    try: error['details']['partial_capture']=prepared['writer'].fail(copy.deepcopy(error))
                    except Exception: error['details']['partial_capture']=prepared['writer'].result
                if submitted and not advanced:
                    with self.state_lock: self.version+=1
                self.last_error=error
                result={'operation_id':ident,'status':'failed','state_version':self.version,'error':error}
                try: self.journal.fail(ident,result)
                except Exception as journal_error:
                    error['details']['journal_failure']=str(journal_error)
                    result['status']='uncertain'
                    self.uncertain_results[ident]={'params':copy.deepcopy(params),'result':copy.deepcopy(result)}
                return result

    def _show(self,prepared):
        req=prepared['request']; result=self.slm.show(req.role,prepared['panel'])
        base={**prepared,'request':req.model_copy(update={'as_restore':False})}
        self.bases[req.role]=base
        if req.as_restore: self.restores[req.role]=copy.deepcopy(base)
        return result

    def _disconnect(self,roles=None):
        requested=['slm1','slm2','ccd'] if roles is None else roles
        result={'restoration':[],'errors':[]}
        for role in requested:
            if role in self.restores and self.slm.status().get(role,{}).get('status')=='connected':
                try:
                    base=self.restores[role]
                    self.slm.show(role,base['panel']); result['restoration'].append(role)
                except Exception as exc: result['errors'].append(f'{role} restore: {exc}')
        slm_roles=[r for r in requested if r!='ccd']
        if slm_roles:
            try: result['slms']=self.slm.disconnect(None if roles is None else slm_roles)
            except Exception as exc: result['errors'].append(f'SLM close: {exc}')
        if 'ccd' in requested:
            try:
                result['ccd']=self.camera.disconnect()
                result['errors'].extend(result['ccd'].get('errors',[]))
            except Exception as exc: result['errors'].append(f'CCD close: {exc}')
        return result

    def close(self):
        with self.operation_lock:
            result=self._disconnect(); self.closed=True; return result
