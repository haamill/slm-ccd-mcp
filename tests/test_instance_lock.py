import pytest
from lab_mcp.instance_lock import InstanceLock


def test_only_one_instance_can_own_runtime(tmp_path):
    with InstanceLock(tmp_path):
        with pytest.raises(OSError):
            with InstanceLock(tmp_path): pass
    with InstanceLock(tmp_path): pass
