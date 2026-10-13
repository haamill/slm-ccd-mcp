from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

SLMRole = Literal['slm1', 'slm2']
Role = Literal['slm1', 'slm2', 'ccd']
Finite = Annotated[float, Field(allow_inf_nan=False, strict=True)]
PositiveInt = Annotated[StrictInt, Field(gt=0)]
Frequency = Annotated[Finite, Field(ge=-0.5, le=0.5)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', validate_assignment=True)


class SLMConfig(Model):
    enabled: bool = True
    serial: str | None = None
    name_contains: str = 'HDSLM'
    desktop_xy: tuple[StrictInt, StrictInt] | None = None
    panel_wh: tuple[PositiveInt, PositiveInt] = (1920, 1200)
    bit_depth: Literal[8, 10] = 10
    offset_xy: tuple[StrictInt, StrictInt] = (10, 61)
    background: Annotated[StrictInt, Field(ge=0, le=1023)] = 0
    restore_source: str | None = None


class CameraConfig(Model):
    camera_id: str | None = None
    expected_model: str = 'IUA24500KMA'


class LabConfig(Model):
    mode: Literal['simulate', 'hardware'] = 'simulate'
    host: str = '127.0.0.1'
    port: Annotated[StrictInt, Field(ge=1, le=65535)] = 8765
    public_base_url: str = 'http://127.0.0.1:8765'
    allowed_hosts: list[str] = ['127.0.0.1:8765', 'localhost:8765']
    allowed_origins: list[str] = ['http://127.0.0.1:8765', 'http://localhost:8765']
    token_env: str = 'LAB_MCP_TOKEN'
    runtime_dir: Path = Path('runtime')
    input_roots: list[Path] = [Path('assets')]
    slm_sdk_dir: Path = Path('D:/ExpSoftware/HDSLM_SDK/Samples/HDSLM_python_api_demo')
    camera_sdk_root: Path = Path('D:/ExpSoftware/toupcamsdk.20260908')
    slms: dict[SLMRole, SLMConfig] = Field(default_factory=lambda: {
        'slm1': SLMConfig(enabled=False, bit_depth=8, offset_xy=(0, 0)), 'slm2': SLMConfig()})
    camera: CameraConfig = Field(default_factory=CameraConfig)
    capture_timeout_max_s: Annotated[Finite, Field(gt=0)] = 120.0


class GratingSpec(Model):
    fx: Frequency = 0.0
    fy: Frequency = 0.0
    phi0: Finite = 0.0
    mode: Literal['code', 'lut'] = 'code'
    lut_source: str | None = None


class LoadRequest(Model):
    role: SLMRole
    source: str
    bit_depth: Literal[8, 10] | None = None
    placement: Literal['centered', 'panel'] = 'centered'
    offset_xy: tuple[StrictInt, StrictInt] | None = None
    background: Annotated[StrictInt, Field(ge=0, le=1023)] | None = None
    packed_rgb: bool = False
    as_restore: bool = False


class CameraPatch(Model):
    exposure_us: Annotated[StrictInt, Field(gt=0, le=4294967295)] | None = None
    gain_percent: Annotated[StrictInt, Field(gt=0, le=65535)] | None = None
    auto_exposure: bool | None = None

    @model_validator(mode='after')
    def check_ae(self):
        if self.exposure_us is not None and self.auto_exposure is True:
            raise ValueError('Explicit exposure requires auto_exposure=false')
        return self


class CaptureRequest(Model):
    frames: Annotated[StrictInt, Field(ge=1, le=16)] = 1
    roi_xywh: tuple[StrictInt, StrictInt, PositiveInt, PositiveInt] | None = None
    settle_s: Annotated[Finite, Field(ge=0)] = 0.3
    discard_frames: Annotated[StrictInt, Field(ge=0, le=64)] = 3
    timeout_s: Annotated[Finite, Field(gt=0)] = 120.0
    preview_bounds: tuple[StrictInt, StrictInt] | None = None

    @model_validator(mode='after')
    def validate_coordinates(self):
        if self.roi_xywh and min(self.roi_xywh[:2]) < 0:
            raise ValueError('ROI origin must be nonnegative')
        if self.preview_bounds and not 0 <= self.preview_bounds[0] < self.preview_bounds[1] <= 65535:
            raise ValueError('Preview bounds must be increasing uint16 values')
        return self


class JointRequest(Model):
    loads: list[LoadRequest] = Field(default_factory=list, max_length=2)
    camera_patch: CameraPatch | None = None
    capture: CaptureRequest = Field(default_factory=CaptureRequest)

    @model_validator(mode='after')
    def distinct_roles(self):
        if len({load.role for load in self.loads}) != len(self.loads):
            raise ValueError('Each SLM role may appear only once')
        return self


@dataclass(frozen=True)
class PreparedPanel:
    codes: np.ndarray
    metadata: dict[str, Any]


@dataclass(frozen=True)
class FrameRecord:
    raw: np.ndarray
    metadata: dict[str, Any]
