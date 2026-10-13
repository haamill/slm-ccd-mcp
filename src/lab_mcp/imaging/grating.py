import numpy as np
from ..models import GratingSpec
from .io import checked_codes, check_shape


def phase_ramp(shape, spec):
    h,w=shape
    x=np.arange(w)-w//2
    y=np.arange(h)-h//2
    return 2*np.pi*(spec.fx*x[None,:]+spec.fy*y[:,None])+spec.phi0


def add_phase_grating(codes, spec, *, lut=None):
    a=checked_codes(codes)
    modulus=256 if a.dtype==np.uint8 else 1024
    ramp=phase_ramp(a.shape,spec)
    if spec.mode=='code':
        return ((a.astype(np.int64)+np.rint(ramp*modulus/(2*np.pi)).astype(np.int64))%modulus).astype(a.dtype)
    if lut is None or np.asarray(lut).shape!=(modulus,) or not np.isfinite(lut).all():
        raise ValueError('LUT mode requires a finite phase LUT matching code depth')
    phases,indices=np.unique(np.asarray(lut)%(2*np.pi),return_index=True)
    target=(np.asarray(lut)[a]+ramp)%(2*np.pi)
    upper=np.searchsorted(phases,target)%len(phases)
    lower=(upper-1)%len(phases)
    dl=np.abs((target-phases[lower]+np.pi)%(2*np.pi)-np.pi)
    du=np.abs((target-phases[upper]+np.pi)%(2*np.pi)-np.pi)
    ties=np.isclose(dl,du,atol=1e-12,rtol=0)
    chosen=np.where(ties,np.minimum(indices[lower],indices[upper]),np.where(dl<du,indices[lower],indices[upper]))
    return chosen.astype(a.dtype)


def make_amplitude_grating(width,height,*,fx,fy,style,low,high,duty=.5):
    if type(width) is not int or type(height) is not int:
        raise ValueError('Dimensions must be integers')
    check_shape((height,width))
    if type(low) is not int or type(high) is not int or not 0<=low<=high<=255:
        raise ValueError('Amplitude endpoints must be uint8 codes')
    if not np.isfinite(duty) or not 0<duty<1:
        raise ValueError('Duty must be between zero and one')
    spec=GratingSpec(fx=fx,fy=fy)
    phase=phase_ramp((height,width),spec)
    if style=='binary':
        value=np.where((phase/(2*np.pi))%1<duty,high,low)
    elif style=='sinusoidal':
        value=low+(high-low)*(1+np.cos(phase))/2
    else:
        raise ValueError('Style must be binary or sinusoidal')
    return np.rint(value).astype(np.uint8)
