import threading
from pathlib import Path
import numpy as np
import pytest
from lab_mcp.devices.hdslm import HDSLMOwner
from lab_mcp.models import SLMConfig, PreparedPanel


class FakeSDK:
    def __init__(self):
        self.calls=[]; self.enum_calls=0; self.opened=set(); self.show_calls=0; self.fail_show=False
        self.dead=False; self.topology_rectangles=[(0,0,4,2)]
        self.lib=self
    def record(self,name): self.calls.append((name,threading.get_ident()))
    def list_displays(self):
        self.record('enum'); self.enum_calls+=1
        return [{'index':1,'sn':'same','name':'HDSLM','x':0,'y':0,'width':4,'height':2}]
    def open(self,index,**kwargs): self.record('open'); self.opened.add(index)
    def close(self,index): self.record('close'); self.opened.discard(index)
    def set_offset(self,*args): self.record('offset')
    def SLM_ADD_PhaseEnabled(self,index,flag): self.record('overlay'); assert flag is False; return 0
    def _check(self,*args): pass
    def pump(self): self.record('pump')
    def show_array(self,index,codes,bit_flags):
        self.record('show'); self.show_calls+=1
        assert index in self.opened and bit_flags==1024 and codes.shape==(2,4)
        if self.fail_show: raise RuntimeError('native call failed')
    def window_alive(self,index): return not self.dead
    def window_hung(self,index): return False


@pytest.fixture
def pair():
    sdk=FakeSDK()
    cfg={'slm1':SLMConfig(enabled=False,bit_depth=8,offset_xy=(0,0)),
         'slm2':SLMConfig(serial='same',desktop_xy=(0,0),panel_wh=(4,2),offset_xy=(0,0))}
    owner=HDSLMOwner(cfg,Path('.'),sdk_factory=lambda:sdk)
    yield owner,sdk
    owner.disconnect()


def test_enum_once_same_thread(pair):
    owner,sdk=pair; owner.connect(['slm2']); owner.status(); owner.status()
    owner.show('slm2',PreparedPanel(np.zeros((2,4),dtype=np.uint16),{'bit_depth':10}))
    assert sdk.enum_calls==1
    assert len({ident for _,ident in sdk.calls})==1
    assert next(iter({ident for _,ident in sdk.calls}))!=threading.get_ident()


def test_missing_slm1_slm2_works(pair):
    owner,sdk=pair; result=owner.connect(['slm1','slm2'])
    assert result['slm1']['status']=='unavailable'
    assert result['slm2']['status']=='connected'


def test_show_error_is_not_retried(pair):
    owner,sdk=pair; owner.connect(['slm2']); sdk.fail_show=True
    with pytest.raises(Exception): owner.show('slm2',PreparedPanel(np.zeros((2,4),dtype=np.uint16),{'bit_depth':10}))
    assert sdk.show_calls==1


def test_window_closed_stops_role(pair):
    owner,sdk=pair; owner.connect(['slm2']); sdk.dead=True
    with pytest.raises(Exception): owner.show('slm2',PreparedPanel(np.zeros((2,4),dtype=np.uint16),{'bit_depth':10}))
    assert sdk.show_calls==0


def test_topology_change_requires_rebind(pair):
    owner,sdk=pair; owner.connect(['slm2']); sdk.topology_rectangles=[(10,0,4,2)]
    with pytest.raises(Exception): owner.show('slm2',PreparedPanel(np.zeros((2,4),dtype=np.uint16),{'bit_depth':10}))
    assert sdk.show_calls==0


def test_no_soft_gamma_or_trigger_calls(pair):
    owner,sdk=pair; owner.connect(['slm2']); owner.disconnect()
    assert all('gamma' not in name and 'trigger' not in name for name,_ in sdk.calls)


def test_shutdown_closes_every_opened_role(pair):
    owner,sdk=pair; owner.connect(['slm2']); owner.disconnect()
    assert not sdk.opened
