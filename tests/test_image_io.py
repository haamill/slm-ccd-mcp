import numpy as np
import pytest
from PIL import Image
from lab_mcp.imaging.io import read_codes


def test_native10_and_rgb_rejection(tmp_path):
    path = tmp_path / 'codes.npy'
    np.save(path, np.array([[0, 1023]], dtype=np.uint16))
    np.testing.assert_array_equal(read_codes(path), [[0, 1023]])
    np.save(path, np.array([[1024]], dtype=np.uint16))
    with pytest.raises(ValueError):
        read_codes(path)
    rgb = tmp_path / 'packed.png'
    Image.fromarray(np.array([[[224,224,240],[0,0,16]]], dtype=np.uint8)).save(rgb)
    with pytest.raises(ValueError):
        read_codes(rgb)
    np.testing.assert_array_equal(read_codes(rgb, packed_rgb=True), [[1023, 1]])
    Image.fromarray(np.array([[[1,1,1]]], dtype=np.uint8)).save(rgb)
    with pytest.raises(ValueError):
        read_codes(rgb, packed_rgb=True)


def test_forged_npy_shape_rejected_before_allocation(tmp_path):
    path = tmp_path / 'giant.npy'
    with path.open('wb') as f:
        np.lib.format.write_array_header_1_0(f, {'descr':'<u2','fortran_order':False,'shape':(2**30,2**30)})
    with pytest.raises((ValueError, OSError)):
        read_codes(path)


def test_huge_image_header_rejected(tmp_path):
    path=tmp_path/'giant.png'
    Image.new('L',(8193,1)).save(path)
    with pytest.raises(ValueError):
        read_codes(path)
