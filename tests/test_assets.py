import hashlib
import io
import numpy as np
import pytest
from lab_mcp.storage.assets import AssetStore


def data():
    stream=io.BytesIO()
    np.save(stream,np.array([[0,1023]],dtype=np.uint16))
    return stream.getvalue()


def test_upload_limits_and_sha(tmp_path):
    store=AssetStore(tmp_path,[tmp_path/'input'])
    blob=data()
    info=store.begin('x.npy',len(blob),hashlib.sha256(blob).hexdigest())
    with pytest.raises(ValueError): store.resolve('asset:'+info['upload_id'])
    with pytest.raises(ValueError): store.chunk(info['upload_id'],0,b'x'*(1048576+1))
    store.chunk(info['upload_id'],0,blob)
    finished=store.finish(info['upload_id'])
    assert store.resolve('asset:'+finished['asset_id']).is_file()
    with pytest.raises(ValueError): store.begin('x.npy',33554433,'0'*64)
    bad=store.begin('x.npy',len(blob),'0'*64)
    store.chunk(bad['upload_id'],0,blob)
    with pytest.raises(ValueError): store.finish(bad['upload_id'])


def test_path_escape_and_symlink(tmp_path):
    root=tmp_path/'input'; root.mkdir()
    outside=tmp_path/'outside.npy'; outside.write_bytes(data())
    store=AssetStore(tmp_path/'runtime',[root])
    with pytest.raises(ValueError): store.resolve(str(outside))
    link=root/'link.npy'
    try: link.symlink_to(outside)
    except OSError: pytest.skip('Windows symlink creation unavailable')
    with pytest.raises(ValueError): store.resolve(str(link))


def test_duplicate_chunk_is_checked(tmp_path):
    store=AssetStore(tmp_path,[]); blob=data()
    info=store.begin('x.npy',len(blob),hashlib.sha256(blob).hexdigest())
    store.chunk(info['upload_id'],0,blob)
    store.chunk(info['upload_id'],0,blob)
    with pytest.raises(ValueError): store.chunk(info['upload_id'],0,b'bad')
