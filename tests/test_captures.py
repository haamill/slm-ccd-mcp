import numpy as np
import pytest
from lab_mcp.models import CaptureRequest, FrameRecord
from lab_mcp.storage.captures import CaptureStore


def test_partial_capture_survives_write_failure(tmp_path):
    store=CaptureStore(tmp_path)
    writer=store.prepare(CaptureRequest(),(3,1),12)
    writer.write_frame(FrameRecord(np.array([[1,2,4095]],dtype=np.uint16),{'host_frame_counter':7}))
    partial=writer.fail({'message':'disk write failed'})
    assert partial['status']=='partial'
    assert partial['saved_frames']==1
    raw=store.registered_file(partial['capture_id'],'raw_000.npy')
    np.testing.assert_array_equal(np.load(raw),[[1,2,4095]])


def test_raw_and_preview_separate(tmp_path):
    store=CaptureStore(tmp_path)
    writer=store.prepare(CaptureRequest(),(2,1),12)
    writer.write_frame(FrameRecord(np.array([[0,2048]],dtype=np.uint16),{}))
    result=writer.finish({})
    assert result['status']=='captured'
    np.testing.assert_array_equal(np.load(store.registered_file(result['capture_id'],'raw_000.npy')),[[0,2048]])
    assert store.registered_file(result['capture_id'],'preview.png').read_bytes().startswith(b'\x89PNG')


def test_disk_full_precheck(tmp_path,monkeypatch):
    import lab_mcp.storage.captures as captures
    monkeypatch.setattr(captures.shutil,'disk_usage',lambda _:type('Usage',(),{'free':0})())
    with pytest.raises(OSError): CaptureStore(tmp_path).prepare(CaptureRequest(),(2,1),12)


def test_unregistered_download_rejected(tmp_path):
    with pytest.raises(ValueError): CaptureStore(tmp_path).registered_file('../x','secret')
