import numpy as np
import pytest
from lab_mcp.models import GratingSpec
from lab_mcp.imaging.grating import add_phase_grating, make_amplitude_grating


def test_code_carrier_quarter_cycle():
    out=add_phase_grating(np.zeros((1,4),dtype=np.uint16),GratingSpec(fx=.25))
    np.testing.assert_array_equal(out,[[512,768,0,256]])


def test_circular_lut_wrap_and_tie():
    lut=np.full(1024,np.pi)
    lut[0]=2*np.pi-.1
    lut[1]=.1
    out=add_phase_grating(np.array([[1]],dtype=np.uint16),GratingSpec(mode='lut',phi0=-.16),lut=lut)
    assert out[0,0]==0
    out=add_phase_grating(np.array([[100]],dtype=np.uint16),GratingSpec(mode='lut'),lut=np.zeros(1024))
    assert out[0,0]==0
    with pytest.raises(ValueError):
        add_phase_grating(np.zeros((1,1),dtype=np.uint16),GratingSpec(mode='lut'))


def test_grating_repeat_identical():
    base=np.array([[200,300,400,500]],dtype=np.uint16)
    spec=GratingSpec(fx=.25)
    np.testing.assert_array_equal(add_phase_grating(base,spec),add_phase_grating(base,spec))
    np.testing.assert_array_equal(base,[[200,300,400,500]])


def test_amplitude_binary_duty():
    out=make_amplitude_grating(4,1,fx=.25,fy=0.,style='binary',low=0,high=255,duty=.5)
    assert out.dtype==np.uint8
    assert np.count_nonzero(out==255)==2
    assert set(out.ravel())=={0,255}
