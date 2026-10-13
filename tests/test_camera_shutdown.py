from test_camera_settings import make_adapter
from lab_mcp.models import CameraPatch


def test_stop_restore_close_all_attempted():
    adapter,c=make_adapter(); adapter.connect(); adapter.apply_settings(CameraPatch(exposure_us=6000))
    def failed_stop(): c.calls.append('stop'); raise RuntimeError('stop failed')
    c.Stop=failed_stop
    result=adapter.disconnect()
    assert 'close' in c.calls and result['errors']
    assert c.exposure==1000 and c.ae==1
