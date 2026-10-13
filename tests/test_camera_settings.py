from types import SimpleNamespace
from pathlib import Path
import pytest
from lab_mcp.devices.toupcam import ToupCamAdapter
from lab_mcp.models import CameraConfig, CameraPatch


class FakeCamera:
    def __init__(self):
        self.ae=1; self.exposure=1000; self.gain=100; self.opts={1:0,2:0,3:0}; self.calls=[]; self.mismatch=False
    def get_AutoExpoEnable(self): return self.ae
    def get_ExpoTime(self): return self.exposure+1 if self.mismatch else self.exposure
    def get_ExpoAGain(self): return self.gain
    def get_ExpTimeRange(self): return (1,1000000,1000)
    def get_ExpoAGainRange(self): return (100,500,100)
    def get_Option(self,key): return self.opts[key]
    def put_Option(self,key,val): self.opts[key]=val; self.calls.append('option')
    def put_AutoExpoEnable(self,val): self.ae=val; self.calls.append('ae')
    def put_ExpoTime(self,val): self.exposure=val; self.calls.append('exposure')
    def put_ExpoAGain(self,val): self.gain=val; self.calls.append('gain')
    def get_RawFormat(self): return (int.from_bytes(b'YYYY','little'),12)
    def get_Size(self): return (4,2)
    def StartPullModeWithCallback(self,callback,context): self.callback=callback; self.calls.append('start')
    def Stop(self): self.calls.append('stop')
    def Close(self): self.calls.append('close')


def make_adapter():
    camera=FakeCamera()
    device=SimpleNamespace(id='camera',displayname='IUA24500KMA',model=SimpleNamespace(flag=1))
    sdk=SimpleNamespace(TOUPCAM_OPTION_RAW=1,TOUPCAM_OPTION_BITDEPTH=2,TOUPCAM_OPTION_RGB=3,TOUPCAM_FLAG_MONO=1,
        Toupcam=SimpleNamespace(EnumV2=lambda:[device],Open=lambda ident:camera))
    return ToupCamAdapter(CameraConfig(),Path('.'),sdk_factory=lambda:sdk),camera


def test_manual_exposure_disables_ae_and_reads_back():
    adapter,c=make_adapter()
    try:
        adapter.connect(); result=adapter.apply_settings(CameraPatch(exposure_us=6000,gain_percent=100))
        assert result['auto_exposure']==0 and result['exposure_us']==6000 and result['gain_percent']==100
    finally: adapter.disconnect()


def test_readback_mismatch_is_error():
    adapter,c=make_adapter()
    try:
        adapter.connect(); c.mismatch=True
        with pytest.raises(Exception): adapter.apply_settings(CameraPatch(exposure_us=6000))
    finally: adapter.disconnect()
