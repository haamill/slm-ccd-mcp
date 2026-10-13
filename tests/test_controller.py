import concurrent.futures
import uuid
import pytest
from lab_mcp.config import load_config
from lab_mcp.models import LabConfig, SLMConfig
from lab_mcp.devices.simulated import SimulatedSLM, SimulatedCamera
from lab_mcp.controller import LabController
from lab_mcp.storage.assets import AssetStore
from lab_mcp.storage.captures import CaptureStore
from lab_mcp.storage.journal import OperationJournal


def make_controller(tmp_path,both=False):
    cfg=LabConfig(runtime_dir=tmp_path,slms={'slm1':SLMConfig(enabled=both,bit_depth=8,offset_xy=(0,0)),
        'slm2':SLMConfig()})
    assets=AssetStore(tmp_path,[]); slm=SimulatedSLM(cfg.slms); camera=SimulatedCamera(slm=slm)
    controller=LabController(cfg,slm,camera,assets,CaptureStore(tmp_path),OperationJournal(tmp_path/'operations.sqlite'))
    controller.execute('lab_connect',{})
    return controller


def test_concurrent_same_id_executes_once(tmp_path):
    c=make_controller(tmp_path); ident=str(uuid.uuid4())
    args={'role':'slm2','gray':7,'bit_depth':10}
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:c.execute('slm_show_uniform',args,operation_id=ident),range(2)))
    assert results[0]==results[1]
    assert c.slm.status()['slm2']['show_count']==1


def test_version_conflict_precedes_sdk(tmp_path):
    c=make_controller(tmp_path)
    with pytest.raises(Exception): c.execute('slm_show_uniform',{'role':'slm2','gray':7,'bit_depth':10},expected_version=0)
    assert c.slm.status()['slm2']['show_count']==0


def test_uncertain_operation_not_replayed(tmp_path):
    c=make_controller(tmp_path); ident=str(uuid.uuid4()); args={'role':'slm2','gray':7,'bit_depth':10}
    c.journal.begin(ident,{'op':'slm_show_uniform','args':args,'expected_version':None})
    c.journal=OperationJournal(c.config.runtime_dir/'operations.sqlite')
    result=c.execute('slm_show_uniform',args,operation_id=ident)
    assert result['status']=='uncertain'
    assert c.slm.status()['slm2']['show_count']==0


def test_repeat_offset_grating_restore_from_original(tmp_path):
    import numpy as np
    c=make_controller(tmp_path)
    asset=c.assets.register_codes(np.full((1000,1000),17,dtype=np.uint16),'image')
    c.execute('slm_load_image',{'role':'slm2','source':'asset:'+asset['asset_id'],'as_restore':True})
    original=c.slm.status()['slm2']['last']['displayed_array_sha256']
    c.execute('slm_set_grating',{'fx':.02,'fy':0.})
    first=c.slm.status()['slm2']['last']['displayed_array_sha256']
    c.execute('slm_set_grating',{'fx':.02,'fy':0.})
    assert c.slm.status()['slm2']['last']['displayed_array_sha256']==first
    c.execute('slm_set_offset',{'role':'slm2','offset_x_px':11,'offset_y_px':61})
    c.execute('slm_restore',{'role':'slm2'})
    assert c.slm.status()['slm2']['last']['displayed_array_sha256']==original
