import hashlib
import numpy as np
from ..models import PreparedPanel
from .io import checked_codes


def array_hash(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def compose_panel(codes, config, request):
    a = checked_codes(codes)
    actual_bits = 8 if a.dtype.itemsize == 1 else 10
    declared_bits=config.bit_depth if request.bit_depth is None else request.bit_depth
    if actual_bits != declared_bits or (request.role == 'slm1' and actual_bits != 8):
        raise ValueError('Explicit bit depth does not match input/device')
    w, h = config.panel_wh
    background = config.background if request.background is None else request.background
    if not 0 <= background < (1 << actual_bits):
        raise ValueError('Background exceeds selected bit depth')
    if request.placement == 'panel':
        if a.shape != (h,w) or request.offset_xy not in (None, (0,0)):
            raise ValueError('Panel input must match native size and have no offset')
        output = a
        x,y,offset = 0,0,(0,0)
    else:
        offset = request.offset_xy if request.offset_xy is not None else config.offset_xy
        x,y = (w-a.shape[1])//2+offset[0], (h-a.shape[0])//2+offset[1]
        if x < 0 or y < 0 or x+a.shape[1] > w or y+a.shape[0] > h:
            raise ValueError('Image and offset do not fit panel; cropping is forbidden')
        output = np.full((h,w),background,dtype=a.dtype)
        output[y:y+a.shape[0],x:x+a.shape[1]] = a
    return PreparedPanel(output, {'input_shape':list(a.shape),'panel_wh':[w,h],
        'placement_xy':[x,y],'offset_xy':list(offset),'bit_depth':actual_bits,
        'input_sha256':array_hash(a),'displayed_array_sha256':array_hash(output)})
