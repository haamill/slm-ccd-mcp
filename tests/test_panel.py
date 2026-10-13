import numpy as np
import pytest
from lab_mcp.models import SLMConfig, LoadRequest
from lab_mcp.imaging.panel import compose_panel


def test_current_1000_alignment():
    codes=np.full((1000,1000),17,dtype=np.uint16)
    panel=compose_panel(codes,SLMConfig(),LoadRequest(role='slm2',source='test.npy'))
    assert panel.metadata['placement_xy']==[470,161]
    np.testing.assert_array_equal(panel.codes[161:1161,470:1470],codes)
    assert panel.codes[160,470]==0


def test_panel_has_no_second_offset():
    codes=np.full((1200,1920),7,dtype=np.uint16)
    panel=compose_panel(codes,SLMConfig(),LoadRequest(role='slm2',source='test.npy',placement='panel'))
    np.testing.assert_array_equal(panel.codes,codes)
    assert panel.metadata['placement_xy']==[0,0]


def test_out_of_bounds_keeps_input():
    codes=np.full((1000,1000),17,dtype=np.uint16)
    with pytest.raises(ValueError):
        compose_panel(codes,SLMConfig(),LoadRequest(role='slm2',source='x',offset_xy=(1000,0)))
    assert np.all(codes==17)
