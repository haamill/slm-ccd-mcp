from pathlib import Path
import tomllib
from .models import LabConfig


def load_config(path: Path, *, mode: str | None = None) -> LabConfig:
    path = path.resolve(strict=True)
    data = tomllib.loads(path.read_text(encoding='utf-8'))
    if mode is not None:
        data['mode'] = mode
    cfg = LabConfig.model_validate(data)
    root = path.parent.parent if path.parent.name == 'config' else path.parent
    for key in ('runtime_dir', 'slm_sdk_dir', 'camera_sdk_root'):
        value = getattr(cfg, key)
        setattr(cfg, key, (root / value).resolve() if not value.is_absolute() else value.resolve())
    cfg.input_roots = [(root / p).resolve() if not p.is_absolute() else p.resolve() for p in cfg.input_roots]
    return cfg
