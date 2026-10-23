import pytest

from posture import state as state_module


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Chaque test a ses propres reglages, sans toucher a %APPDATA%."""
    monkeypatch.setattr(state_module, "SETTINGS_FILE", tmp_path / "settings.json")
    s = state_module.state
    monkeypatch.setattr(s, "settings", dict(state_module.DEFAULTS))
    monkeypatch.setattr(s, "status", {"state": "starting"})
    monkeypatch.setattr(s, "calib_start", None)
    monkeypatch.setattr(s, "calib_samples", [])
    return tmp_path
