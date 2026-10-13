import threading
import time
import numpy as np
import pytest
from test_controller import make_controller


def test_joint_preflight_before_any_mutation(tmp_path):
    c=make_controller(tmp_path)
    a=c.assets.register_codes(np.zeros((1000,1000),dtype=np.uint16),'base')
    with pytest.raises(Exception): c.execute('lab_load_and_capture',{'loads':[
        {'role':'slm2','source':'asset:'+a['asset_id']}, {'role':'slm1','source':'missing.npy','bit_depth':8}]})
    assert c.slm.status()['slm2']['show_count']==0


def test_joint_order_and_no_interleaving(tmp_path):
    c=make_controller(tmp_path,both=True); events=[]
    show=c.slm.show; settings=c.camera.apply_settings; capture=c.camera.capture
    c.slm.show=lambda role,panel:(events.append(role+'.show'),show(role,panel))[1]
    c.camera.apply_settings=lambda patch:(events.append('camera.settings'),settings(patch))[1]
    c.camera.capture=lambda *args:(events.append('camera.capture'),capture(*args))[1]
    assets=[c.assets.register_codes(np.zeros((1,1),dtype=dtype),'base') for dtype in (np.uint8,np.uint16)]
    result=c.execute('lab_load_and_capture',{'loads':[
        {'role':'slm1','source':'asset:'+assets[0]['asset_id'],'bit_depth':8},
        {'role':'slm2','source':'asset:'+assets[1]['asset_id']}],
        'camera_patch':{'exposure_us':6000},'capture':{'settle_s':0.,'discard_frames':0}})
    assert result['status']=='succeeded'
    assert events==['camera.settings','slm2.show','slm1.show','camera.capture']


def test_save_failure_reports_submitted_stage(tmp_path,monkeypatch):
    c=make_controller(tmp_path)
    from lab_mcp.storage.captures import CaptureWriter
    monkeypatch.setattr(CaptureWriter,'write_frame',lambda *args:(_ for _ in ()).throw(OSError('disk failure')))
    result=c.execute('ccd_capture',{'settle_s':0.,'discard_frames':0})
    assert result['status']=='failed'
    assert result['error']['hardware_submitted']
    assert result['error']['details']['partial_capture']['status']=='partial'


def test_status_during_capture_is_responsive(tmp_path):
    c=make_controller(tmp_path); entered=threading.Event(); release=threading.Event(); original=c.camera.capture
    def slow(*args): entered.set(); release.wait(2); return original(*args)
    c.camera.capture=slow
    thread=threading.Thread(target=lambda:c.execute('ccd_capture',{'settle_s':0.,'discard_frames':0}))
    thread.start(); assert entered.wait(1)
    start=time.perf_counter(); assert c.status()['mode']=='simulate'; assert time.perf_counter()-start<.2
    release.set(); thread.join(2); assert not thread.is_alive()
