import io
import numpy as np
from PIL import Image


def make_preview(raw,effective_bits,*,bounds=None,max_side=1024):
    a=np.asarray(raw)
    if a.ndim!=2 or a.size==0 or not 8<=effective_bits<=16 or max_side<1:
        raise ValueError('Invalid RAW shape, effective depth or preview dimensions')
    black,white=bounds if bounds is not None else (0,(1<<effective_bits)-1)
    if not 0<=black<white<=65535:
        raise ValueError('Invalid fixed preview range')
    mapped=np.rint(np.clip((a.astype(np.float64)-black)/(white-black),0,1)*255).astype(np.uint8)
    image=Image.fromarray(mapped)
    image.thumbnail((max_side,max_side),Image.Resampling.BOX)
    buffer=io.BytesIO()
    image.save(buffer,format='PNG')
    return buffer.getvalue(), {'black':black,'white':white,'effective_bits':effective_bits,
        'preview_wh':list(image.size),'mapping':'fixed_linear','min':int(a.min()),'max':int(a.max()),
        'mean':float(a.mean()),'near_full_fraction':float(np.mean(a>=.995*((1<<effective_bits)-1)))}
