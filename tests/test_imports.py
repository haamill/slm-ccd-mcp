import importlib
import ctypes
import os


def test_imports_do_not_load_vendor(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('vendor DLL loaded during import')
    monkeypatch.setattr(ctypes, 'WinDLL', forbidden)
    monkeypatch.setattr(os, 'add_dll_directory', forbidden)
    importlib.import_module('lab_mcp.config')
    importlib.import_module('lab_mcp.models')
