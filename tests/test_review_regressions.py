import json
import os
from pathlib import Path
import subprocess
import uuid
import numpy as np
import pytest
from lab_mcp.devices.hdslm import HDSLMOwner
from lab_mcp.errors import LabError
from lab_mcp.models import SLMConfig, PreparedPanel
from lab_mcp.storage.assets import AssetStore
from lab_mcp.storage.captures import CaptureStore
from lab_mcp.storage.journal import OperationJournal
from test_slm_owner import FakeSDK
from test_controller import make_controller
from test_camera_settings import make_adapter


def junction(link, target):
    if os.name == 'nt':
        quote=lambda p: "'"+str(p).replace("'", "''")+"'"
        subprocess.run(['powershell','-NoProfile','-Command',
            'New-Item -ItemType Junction -Path '+quote(link)+' -Target '+quote(target)+' | Out-Null'],check=True)
    else: link.symlink_to(target, target_is_directory=True)


def test_capture_directory_junction_rejected_before_manifest_read(tmp_path,monkeypatch):
    store=CaptureStore(tmp_path/'runtime'); ident=str(uuid.uuid4())
    outside=tmp_path/'outside'; outside.mkdir()
    (outside/'manifest.json').write_text('{"files":{}}')
    junction(store.root/ident,outside)
    import lab_mcp.storage.captures as module
    reads=[]; original=module.read_json
    monkeypatch.setattr(module,'read_json',lambda path:(reads.append(path),original(path))[1])
    with pytest.raises(ValueError): store.registered_file(ident,'manifest.json')
    assert reads==[]


def test_asset_directory_junction_and_metadata_symlink_rejected(tmp_path,monkeypatch):
    store=AssetStore(tmp_path/'runtime',[]); ident=str(uuid.uuid4())
    outside=tmp_path/'outside'; outside.mkdir()
    (outside/(ident+'.json')).write_text(json.dumps({'suffix':'.npy'}))
    np.save(outside/(ident+'.npy'),np.zeros((1,1),dtype=np.uint16))
    # Replace the published root with a junction after its trusted startup path was fixed.
    store.pending.rmdir(); store.root.rmdir(); junction(store.root,outside)
    import lab_mcp.storage.assets as module
    reads=[]; original=module.read_json
    monkeypatch.setattr(module,'read_json',lambda path:(reads.append(path),original(path))[1])
    with pytest.raises(ValueError): store.resolve('asset:'+ident)
    assert reads==[]


def test_capture_file_symlink_rejected(tmp_path):
    store=CaptureStore(tmp_path/'runtime'); ident=str(uuid.uuid4())
    directory=store.root/ident; directory.mkdir()
    outside=tmp_path/'external.json'; outside.write_text('{"files":{}}')
    try: (directory/'manifest.json').symlink_to(outside)
    except OSError: pytest.skip('Windows file symlink privilege unavailable')
    with pytest.raises(ValueError): store.registered_file(ident,'manifest.json')


class TwoSDK(FakeSDK):
    def __init__(self):
        super().__init__(); self.topology_rectangles=[(0,0,4,2),(4,0,4,2)]
        self.fail_close=True; self.close_attempts=[]
    def list_displays(self):
        return [{'index':i,'sn':'same','name':'HDSLM','x':4*(i-1),'y':0,'width':4,'height':2} for i in (1,2)]
    def close(self,index):
        self.close_attempts.append(index)
        if index==1 and self.fail_close: raise RuntimeError('injected close failure')
        super().close(index)


def two_owner():
    sdk=TwoSDK(); cfg={r:SLMConfig(serial='same',desktop_xy=(4*i,0),panel_wh=(4,2)) for i,r in enumerate(('slm1','slm2'))}
    return HDSLMOwner(cfg,Path('.'),sdk_factory=lambda:sdk),sdk


def test_failed_close_retains_role_and_attempts_remaining():
    owner,sdk=two_owner()
    try:
        owner.connect(['slm1','slm2'])
        with pytest.raises(LabError): owner.disconnect(['slm1','slm2'])
        assert sdk.close_attempts==[1,2]
        assert set(owner.opened)=={'slm1'}
        sdk.fail_close=False; owner.disconnect(['slm1'])
        assert not sdk.opened
    finally: sdk.fail_close=False; owner.disconnect()


def test_full_shutdown_attempts_all_and_terminates_after_error():
    owner,sdk=two_owner(); owner.connect(['slm1','slm2'])
    with pytest.raises(LabError): owner.disconnect()
    assert 2 in sdk.close_attempts
    assert owner.thread is None or not owner.thread.is_alive()
    assert 'slm1' in owner.opened  # unresolved native close remains tracked


def test_added_monitor_latches_requires_rebind():
    sdk=FakeSDK(); cfg={'slm2':SLMConfig(serial='same',desktop_xy=(0,0),panel_wh=(4,2))}
    owner=HDSLMOwner(cfg,Path('.'),sdk_factory=lambda:sdk)
    try:
        owner.connect(['slm2']); sdk.topology_rectangles.append((4,0,4,2))
        panel=PreparedPanel(np.zeros((2,4),dtype=np.uint16),{'bit_depth':10})
        with pytest.raises(LabError): owner.show('slm2',panel)
        sdk.topology_rectangles.pop()
        with pytest.raises(LabError): owner.connect(['slm2'])
        assert sdk.show_calls==0 and sdk.enum_calls==1
    finally: owner.disconnect()


def test_identity_replaced_at_same_rectangle_stops_connect_before_open():
    sdk=FakeSDK(); sdk.topology_records=[('monitor-A',(0,0,4,2))]
    cfg={'slm2':SLMConfig(serial='same',desktop_xy=(0,0),panel_wh=(4,2))}
    owner=HDSLMOwner(cfg,Path('.'),sdk_factory=lambda:sdk)
    try:
        owner.connect(['slm2']); owner.disconnect(['slm2'])
        sdk.topology_records=[('monitor-B',(0,0,4,2))]
        with pytest.raises(LabError): owner.connect(['slm2'])
        assert not sdk.opened
    finally: owner.disconnect()


def test_journal_failure_after_submission_returns_uncertain_and_never_replays(tmp_path,monkeypatch):
    c=make_controller(tmp_path); ident=str(uuid.uuid4()); args={'role':'slm2','gray':7,'bit_depth':10}
    def fail(*args): raise OSError('persistent disk failure')
    monkeypatch.setattr(c.journal,'finish',fail); monkeypatch.setattr(c.journal,'fail',fail)
    result=c.execute('slm_show_uniform',args,operation_id=ident)
    assert result['status']=='uncertain' and result['operation_id']==ident
    assert result['error']['hardware_submitted'] and result['error']['stage']=='slm2.show'
    assert result['error']['details']['journal_failure']
    assert c.execute('slm_show_uniform',args,operation_id=ident)==result
    assert c.slm.status()['slm2']['show_count']==1


@pytest.mark.parametrize('state',['error','streaming'])
def test_joint_rejects_unusable_ccd_before_settings_or_show(tmp_path,state):
    c=make_controller(tmp_path); adapter,cam=make_adapter(); adapter.connect(); c.camera=adapter
    asset=c.assets.register_codes(np.zeros((1,1),dtype=np.uint16),'base')
    try:
        adapter.state['status']=state; adapter.queue.publish_error(RuntimeError('latched SDK error'))
        before=list(cam.calls)
        with pytest.raises(LabError): c.execute('lab_load_and_capture',{'loads':[
            {'role':'slm2','source':'asset:'+asset['asset_id']}],'camera_patch':{'exposure_us':6000}})
        assert cam.calls==before and c.slm.status()['slm2']['show_count']==0
    finally: adapter.disconnect()


def test_journal_persists_command_parameters_and_completed_steps_after_restart(tmp_path):
    c=make_controller(tmp_path); ident=str(uuid.uuid4()); args={'role':'slm2','gray':7,'bit_depth':10}
    c.execute('slm_show_uniform',args,operation_id=ident)
    journal=OperationJournal(c.config.runtime_dir/'operations.sqlite')
    record=journal.get(ident)
    assert record['params']=={'op':'slm_show_uniform','args':args,'expected_version':None}
    assert record['steps'][0]['name']=='slm2.show' and record['steps'][0]['status']=='completed'
    assert record['steps'][0]['hardware_submitted']


def test_slm1_defaults_to_eight_bits(tmp_path):
    c=make_controller(tmp_path,both=True)
    a=c.assets.register_codes(np.zeros((1,1),dtype=np.uint8),'amplitude')
    assert c.execute('slm_load_image',{'role':'slm1','source':'asset:'+a['asset_id']})['status']=='succeeded'
    assert c.execute('slm_show_uniform',{'role':'slm1','gray':42,'bit_depth':None})['status']=='succeeded'


def test_huge_finite_phase_is_reduced_before_integer_quantization():
    from lab_mcp.models import GratingSpec
    from lab_mcp.imaging.grating import add_phase_grating
    a=np.zeros((2,3),dtype=np.uint16); phi=1e20
    with np.errstate(invalid='raise',over='raise'):
        actual=add_phase_grating(a,GratingSpec(fx=.1,phi0=phi))
    expected=add_phase_grating(a,GratingSpec(fx=.1,phi0=phi%(2*np.pi)))
    np.testing.assert_array_equal(actual,expected)
