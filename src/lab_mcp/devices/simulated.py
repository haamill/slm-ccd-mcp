import copy
import time
import numpy as np
from ..models import FrameRecord
from ..errors import LabError
from .toupcam import crop_raw


class SimulatedSLM:
    def __init__(self,configs):
        self.configs=configs
        self.states={r:{'status':'disconnected' if c.enabled else 'unavailable','show_count':0} for r,c in configs.items()}
    def connect(self,roles):
        for role in roles:
            self.states[role]['status']='connected' if self.configs[role].enabled else 'unavailable'
            self.states[role]['simulation']=True
            self.states[role]['window']={'alive':self.configs[role].enabled,'unobscured':self.configs[role].enabled}
        return self.status()
    def show(self,role,panel):
        if self.states[role]['status']!='connected': raise LabError('unavailable',f'{role} not connected')
        self.states[role]['show_count']+=1
        result={**panel.metadata,'simulation':True,'submitted_monotonic_ns':time.monotonic_ns()}
        self.states[role]['last']=result
        return copy.deepcopy(result)
    def status(self): return copy.deepcopy(self.states)
    def disconnect(self,roles=None):
        for role in self.states if roles is None else roles:
            self.states[role]['status']='disconnected' if self.configs[role].enabled else 'unavailable'
        return self.status()


class SimulatedCamera:
    def __init__(self,*,slm=None,sensor_wh=(64,48)):
        self.slm=slm; self.sensor_wh=sensor_wh; self.connected=False; self.counter=0
        self.current={'auto_exposure':0,'exposure_us':1000,'gain_percent':100,
            'exposure_range_us':[1,1000000,1000],'gain_range_percent':[100,500,100],
            'sensor_wh':list(sensor_wh),'effective_bits':12}
    def connect(self): self.connected=True; return self.status()
    def settings(self):
        if not self.connected: raise LabError('unavailable','Simulated CCD not connected')
        return {**copy.deepcopy(self.current),'checked_monotonic_ns':time.monotonic_ns()}
    def validate_patch(self,patch):
        s=self.settings()
        for name,range_key in [('exposure_us','exposure_range_us'),('gain_percent','gain_range_percent')]:
            value=getattr(patch,name)
            if value is not None and not s[range_key][0]<=value<=s[range_key][1]: raise ValueError('CCD setting out of range')
    def apply_settings(self,patch):
        self.validate_patch(patch)
        for key,value in patch.model_dump(exclude_none=True).items(): self.current[key]=int(value)
        if patch.exposure_us is not None: self.current['auto_exposure']=0
        return self.settings()
    def capture(self,request,boundary_ns,on_frame):
        s=self.settings(); threshold=int(boundary_ns+(request.settle_s+s['exposure_us']/1e6)*1e9)
        remaining=(threshold-time.monotonic_ns())/1e9
        if remaining>0: time.sleep(remaining+.016)
        discarded=[]; retained=[]
        w,h=self.sensor_wh; yy,xx=np.indices((h,w))
        last=self.slm.status()['slm2'].get('last',{}) if self.slm else {}
        signature=int(last.get('displayed_array_sha256','0000')[:4],16)%1024
        for index in range(request.discard_frames+request.frames):
            self.counter+=1
            raw=((xx+3*yy+signature+self.counter)%4096).astype(np.uint16)
            raw,origin=crop_raw(raw,request.roi_xywh)
            meta={'host_frame_counter':self.counter,'host_monotonic_ns':time.monotonic_ns(),
                'origin_xy':origin,'simulation':True,'exposure_us_setting':s['exposure_us']}
            if index<request.discard_frames: discarded.append(meta)
            else: on_frame(FrameRecord(raw,meta)); retained.append(meta)
        return {'simulation':True,'frames':retained,'discarded':discarded,'settings':s,
            'freshness_threshold_ns':threshold,'screen_done_monotonic_ns':boundary_ns}
    def status(self): return {'status':'streaming' if self.connected else 'disconnected','simulation':True,'settings':copy.deepcopy(self.current)}
    def disconnect(self): self.connected=False; return {'status':'disconnected','errors':[],'simulation':True}
