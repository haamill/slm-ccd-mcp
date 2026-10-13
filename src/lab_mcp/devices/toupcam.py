import copy
import ctypes
import os
from pathlib import Path
import threading
import time
import numpy as np
from ..errors import LabError
from ..models import FrameRecord
from .frame_queue import FreshFrameQueue
from .vendor import load_vendor_module, require_windows_x64


def crop_raw(raw,roi):
    h,w=raw.shape
    if roi is None: return raw.copy(),[0,0]
    x,y,rw,rh=roi
    if min(x,y)<0 or min(rw,rh)<=0 or x+rw>w or y+rh>h: raise ValueError('ROI exceeds full sensor')
    return raw[y:y+rh,x:x+rw].copy(),[x,y]


class ToupCamAdapter:
    def __init__(self,config,sdk_root,*,sdk_factory=None):
        self.config=config; self.sdk_root=Path(sdk_root); self.factory=sdk_factory
        self.sdk=None; self.camera=None; self.dll_handle=None; self.before=None; self.options_before={}
        self.started=False; self.state={'status':'disconnected'}; self.queue=FreshFrameQueue()
        self.pull_lock=threading.Lock(); self.roi=None; self.counter=0

    def settings(self):
        if self.camera is None: raise LabError('unavailable','CCD is not connected')
        c=self.camera
        result={'auto_exposure':c.get_AutoExpoEnable(),'exposure_us':c.get_ExpoTime(),
            'gain_percent':c.get_ExpoAGain(),'exposure_range_us':list(c.get_ExpTimeRange()),
            'gain_range_percent':list(c.get_ExpoAGainRange()),'sensor_wh':list(c.get_Size()),
            'effective_bits':self.bits,'checked_monotonic_ns':time.monotonic_ns()}
        self.state['settings']=result
        return copy.deepcopy(result)

    def connect(self):
        if self.camera is not None: return self.status()
        try:
            if self.factory: self.sdk=self.factory()
            else:
                require_windows_x64()
                self.dll_handle=os.add_dll_directory(str(self.sdk_root/'win/x64'))
                self.sdk=load_vendor_module('lab_vendor_toupcam',self.sdk_root/'python/toupcam.py')
            devices=self.sdk.Toupcam.EnumV2()
            matches=[d for d in devices if (d.id==self.config.camera_id if self.config.camera_id else
                self.config.expected_model.lower() in d.displayname.lower())]
            if len(matches)!=1: raise LabError('camera_binding','Expected exactly one matching CCD')
            device=matches[0]
            if not device.model.flag & self.sdk.TOUPCAM_FLAG_MONO: raise LabError('unsupported_camera','Monochrome RAW CCD required')
            self.camera=self.sdk.Toupcam.Open(device.id)
            if self.camera is None: raise LabError('camera_busy','Unable to open CCD; check other applications')
            c=self.camera
            self.before={'auto_exposure':c.get_AutoExpoEnable(),'exposure_us':c.get_ExpoTime(),'gain_percent':c.get_ExpoAGain()}
            self.options_before={name:c.get_Option(getattr(self.sdk,'TOUPCAM_OPTION_'+name)) for name in ('RAW','BITDEPTH','RGB')}
            c.put_Option(self.sdk.TOUPCAM_OPTION_RAW,1); c.put_Option(self.sdk.TOUPCAM_OPTION_BITDEPTH,1)
            fourcc,self.bits=c.get_RawFormat()
            if int(fourcc).to_bytes(4,'little')!=b'YYYY' or not 8<self.bits<=16:
                raise LabError('raw_format','Expected monochrome YYYY 9..16 effective bits')
            self.width,self.height=c.get_Size()
            self.buffer=ctypes.create_string_buffer(self.width*self.height*2)
            self.queue=FreshFrameQueue(); self.counter=0
            self.state={'status':'connected','camera_id':device.id,'model':device.displayname,
                'sensor_wh':[self.width,self.height],'effective_bits':self.bits,'raw_fourcc':'YYYY',
                'row_order':'SDK buffer order; no vertical flip'}
            self.settings()
            self.started=True
            c.StartPullModeWithCallback(self._on_event,None)
            self.state['status']='streaming'
            return self.status()
        except Exception:
            self.disconnect(); raise

    def validate_patch(self,patch):
        settings=self.settings()
        for key,range_key in [('exposure_us','exposure_range_us'),('gain_percent','gain_range_percent')]:
            value=getattr(patch,key)
            if value is not None and not settings[range_key][0]<=value<=settings[range_key][1]:
                raise ValueError(f'{key} exceeds CCD supported range')

    def apply_settings(self,patch):
        self.validate_patch(patch); c=self.camera
        expected=patch.model_dump(exclude_none=True)
        if patch.exposure_us is not None: expected['auto_exposure']=False
        if expected.get('auto_exposure') is False: c.put_AutoExpoEnable(0)
        if patch.exposure_us is not None: c.put_ExpoTime(patch.exposure_us)
        if patch.gain_percent is not None: c.put_ExpoAGain(patch.gain_percent)
        if expected.get('auto_exposure') is True: c.put_AutoExpoEnable(1)
        result=self.settings()
        if any(result[key]!=value for key,value in expected.items()):
            raise LabError('readback_mismatch','CCD setting readback mismatch',stage='camera.settings',hardware_submitted=True)
        return result

    def _on_event(self,event,context):
        sdk=self.sdk
        if event in (sdk.TOUPCAM_EVENT_ERROR,sdk.TOUPCAM_EVENT_DISCONNECTED):
            self.state['status']='error'; self.queue.publish_error(RuntimeError('CCD SDK error or disconnected')); return
        if event!=sdk.TOUPCAM_EVENT_IMAGE: return
        try:
            with self.pull_lock:
                info=sdk.ToupcamFrameInfoV4()
                self.camera.PullImageV4(self.buffer,0,16,-1,info)
                v=info.v3
                if (v.width,v.height)!=(self.width,self.height): raise ValueError('CCD frame shape changed')
                self.counter+=1
                if not self.queue.active: return
                raw=np.frombuffer(self.buffer,dtype='<u2').reshape(self.height,self.width)
                array,origin=crop_raw(raw,self.roi)
                metadata={'host_monotonic_ns':time.monotonic_ns(),'host_frame_counter':self.counter,
                    'origin_xy':origin,'width':v.width,'height':v.height,'flags':v.flag}
                for field,flag in [('seq','SEQ'),('timestamp','TIMESTAMP'),('expotime','EXPOTIME'),('expogain','EXPOGAIN')]:
                    value=getattr(v,field)
                    if v.flag & getattr(sdk,'TOUPCAM_FRAMEINFO_FLAG_'+flag) and (value>0 or field=='seq'):
                        metadata[field]=value
                self.queue.publish(FrameRecord(array,metadata))
        except Exception as exc: self.queue.publish_error(exc)

    def capture(self,request,boundary_ns,on_frame):
        settings=self.settings()
        minimum=request.settle_s+(request.frames+request.discard_frames+1)*settings['exposure_us']/1e6
        if request.timeout_s<minimum: raise ValueError('Timeout cannot cover exposure, settling and frame count')
        if request.roi_xywh:
            x,y,w,h=request.roi_xywh
            if x+w>self.width or y+h>self.height: raise ValueError('ROI exceeds sensor')
        if self.state['status']!='streaming': raise LabError('unavailable','CCD stream is not usable')
        self.roi=request.roi_xywh
        try:
            result=self.queue.collect(request,boundary_ns,settings['exposure_us'],on_frame)
            result['settings']=settings
            return result
        finally: self.roi=None

    def status(self): return copy.deepcopy(self.state)

    def disconnect(self):
        errors=[]; restoration=[]; c=self.camera
        def attempt(name,function):
            try: function(); restoration.append({'operation':name,'ok':True})
            except Exception as exc: errors.append(f'{name}: {exc}'); restoration.append({'operation':name,'ok':False})
        self.queue.publish_error(RuntimeError('CCD released'))
        if c is not None:
            if self.started: attempt('Stop',c.Stop)
            if self.before is not None:
                attempt('auto_off',lambda:c.put_AutoExpoEnable(0))
                for name,value in self.options_before.items():
                    attempt(name,lambda name=name,value=value:c.put_Option(getattr(self.sdk,'TOUPCAM_OPTION_'+name),value))
                attempt('exposure',lambda:c.put_ExpoTime(self.before['exposure_us']))
                attempt('gain',lambda:c.put_ExpoAGain(self.before['gain_percent']))
                attempt('auto_restore',lambda:c.put_AutoExpoEnable(self.before['auto_exposure']))
                try:
                    after={'auto_exposure':c.get_AutoExpoEnable(),'exposure_us':c.get_ExpoTime(),'gain_percent':c.get_ExpoAGain()}
                    if after!=self.before: errors.append('Restored settings readback mismatch')
                    if any(c.get_Option(getattr(self.sdk,'TOUPCAM_OPTION_'+n))!=v for n,v in self.options_before.items()): errors.append('Restored options readback mismatch')
                except Exception as exc: errors.append(f'Readback: {exc}')
            attempt('Close',c.Close)
        self.camera=None; self.before=None; self.started=False
        if self.dll_handle is not None: self.dll_handle.close(); self.dll_handle=None
        self.state={'status':'disconnected' if not errors else 'restore_failed','errors':errors,'restoration':restoration}
        return self.status()
