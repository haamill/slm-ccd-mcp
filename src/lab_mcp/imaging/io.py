from pathlib import Path
import numpy as np
from PIL import Image

MAX_PIXELS = 8_388_608


def check_shape(shape):
    if len(shape) != 2 or min(shape) <= 0 or max(shape) > 8192 or int(shape[0])*int(shape[1]) > MAX_PIXELS:
        raise ValueError('Image must be a bounded nonempty 2D array')


def checked_codes(array):
    a = np.asarray(array)
    check_shape(a.shape)
    if a.dtype.kind != 'u' or a.dtype.itemsize not in (1, 2):
        raise ValueError('Codes must be uint8 or uint16')
    if a.dtype.itemsize == 2 and int(a.max()) > 1023:
        raise ValueError('Native10 codes exceed 1023')
    return np.array(a, dtype=np.uint8 if a.dtype.itemsize == 1 else np.uint16, order='C', copy=True)


def read_codes(path: Path, *, packed_rgb=False, max_file_bytes=33554432):
    path = Path(path)
    if path.stat().st_size > max_file_bytes:
        raise ValueError('Input exceeds file size limit')
    if path.suffix.lower() == '.npy':
        return checked_codes(np.load(path, allow_pickle=False, mmap_mode='r', max_header_size=4096))
    if path.suffix.lower() not in ('.png', '.bmp'):
        raise ValueError('Only NPY, PNG and BMP are accepted')
    with Image.open(path) as image:
        check_shape((image.height, image.width))
        if image.mode == 'RGB' and packed_rgb:
            rgb = np.asarray(image).astype(np.uint16)
            if np.any(rgb[...,0] & 31) or np.any(rgb[...,1] & 31) or np.any(rgb[...,2] & 15):
                raise ValueError('Invalid vendor RGB10 bit layout')
            return checked_codes(((rgb[...,0] & 224)<<2) | ((rgb[...,1]&224)>>1) | ((rgb[...,2]&240)>>4))
        if image.mode not in ('L', 'I', 'I;16', 'I;16L', 'I;16B'):
            raise ValueError('Expected grayscale or explicitly packed RGB10')
        array = np.asarray(image)
        if image.mode == 'I' and array.min() >= 0 and array.max() <= 1023:
            array = array.astype(np.uint16)
        return checked_codes(array)


def read_phase_lut(path: Path, *, expected_codes=None):
    if Path(path).stat().st_size > 32768 or Path(path).suffix.lower() != '.npy':
        raise ValueError('LUT must be a small NPY file')
    array = np.load(path, allow_pickle=False, mmap_mode='r', max_header_size=4096)
    if array.ndim != 1 or len(array) not in (256, 1024) or array.dtype.kind not in 'fi':
        raise ValueError('LUT must have 256 or 1024 real phase entries')
    if expected_codes is not None and len(array) != expected_codes:
        raise ValueError('LUT bit depth mismatch')
    if not np.isfinite(array).all():
        raise ValueError('LUT phases must be finite')
    return np.array(array, dtype=np.float64, copy=True)
