from pathlib import Path
import ctypes
import pytest
from lab_mcp.cli import main, build_controller
from lab_mcp.config import load_config
from lab_mcp.instance_lock import InstanceLock


def test_cli_simulate_never_loads_vendor(tmp_path,monkeypatch):
    monkeypatch.setattr(ctypes,'WinDLL',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('DLL touched')))
    cfg=load_config(Path('config/simulation.toml')); cfg.runtime_dir=tmp_path
    controller=build_controller(cfg)
    assert controller.status()['mode']=='simulate'
    controller.close()


def test_hardware_flag_and_binding_required(monkeypatch):
    monkeypatch.setenv('LAB_MCP_TOKEN','test-only-secret-0123456789abcdef')
    assert main(['serve','--config','config/hardware.example.toml','--mode','hardware'])!=0


def test_probe_refuses_active_owner(tmp_path):
    config=tmp_path/'local.toml'
    config.write_text('mode="hardware"\nruntime_dir="'+tmp_path.as_posix()+'"\n',encoding='utf-8')
    with InstanceLock(tmp_path):
        assert main(['probe','--config',str(config)])!=0


def test_cli_error_redacts_secrets(monkeypatch,capsys):
    secret='test-only-secret-0123456789abcdef'
    monkeypatch.setenv('LAB_MCP_TOKEN',secret)
    assert main(['serve','--config','config/hardware.example.toml','--mode','hardware'])!=0
    output=capsys.readouterr()
    assert secret not in output.out+output.err
