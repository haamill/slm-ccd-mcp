from pathlib import Path
import pytest
from pydantic import ValidationError
from lab_mcp.config import load_config
from lab_mcp.models import CameraPatch, CaptureRequest, GratingSpec, JointRequest, LoadRequest


def test_slm2_default_alignment():
    cfg = load_config(Path('config/simulation.toml'))
    assert cfg.slms['slm2'].offset_xy == (10, 61)
    assert cfg.slms['slm2'].panel_wh == (1920, 1200)
    assert not cfg.slms['slm1'].enabled


@pytest.mark.parametrize('kwargs', [{'exposure_us': True}, {'exposure_us': 0}, {'gain_percent': -1}])
def test_strict_numbers(kwargs):
    with pytest.raises(ValidationError):
        CameraPatch(**kwargs)


@pytest.mark.parametrize('kwargs', [{'fx': float('nan')}, {'fy': float('inf')}, {'fx': .51}])
def test_invalid_grating(kwargs):
    with pytest.raises(ValidationError):
        GratingSpec(**kwargs)


def test_capture_validation():
    for kwargs in ({'settle_s': float('inf')}, {'frames': True}, {'frames': 17}, {'timeout_s': 0}):
        with pytest.raises(ValidationError):
            CaptureRequest(**kwargs)


def test_conflicting_ae():
    with pytest.raises(ValidationError):
        CameraPatch(exposure_us=6000, auto_exposure=True)


def test_duplicate_joint_roles():
    request = LoadRequest(role='slm2', source='test.npy', bit_depth=10)
    with pytest.raises(ValidationError):
        JointRequest(loads=[request, request])


def test_hardware_requires_explicit_binding():
    cfg = load_config(Path('config/hardware.example.toml'))
    assert cfg.slms['slm2'].desktop_xy is None
    assert cfg.mode == 'hardware'


def test_relative_config_paths_are_project_based(tmp_path):
    cfg = load_config(Path('config/simulation.toml'))
    assert cfg.runtime_dir.is_absolute()
    assert cfg.input_roots[0].name == 'assets'
