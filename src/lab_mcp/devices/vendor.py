import importlib.util
import os
from pathlib import Path
import struct


def require_windows_x64():
    if os.name!='nt' or struct.calcsize('P')!=8:
        raise OSError('Hardware control requires Windows x64 Python')


def load_vendor_module(name,path):
    path=Path(path).resolve(strict=True)
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise ImportError('Cannot load vendor wrapper')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
