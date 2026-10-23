import json

import pytest

from posture import state as state_module
from posture.state import DEFAULTS, load_settings, validate


def test_validate_accepts_good_values():
    good = {"alert_delay": 5, "enabled": False, "overlay_corner": "top-left", "head_threshold": 0.2, "show_pill": True}
    assert validate(good) == good


@pytest.mark.parametrize("bad", [
    {"alert_delay": 0}, {"alert_delay": True}, {"alert_delay": float("nan")}, {"escalation_delay": 1000},
    {"enabled": "oui"}, {"overlay_corner": "middle"}, {"reference": [1, 1, 1]}, {"inconnu": 1},
])
def test_validate_rejects(bad):
    with pytest.raises(ValueError):
        validate(bad)


def test_missing_file_gives_defaults():
    assert load_settings() == DEFAULTS


def test_corrupt_file_gives_defaults():
    state_module.SETTINGS_FILE.write_text("{pas du json", encoding="utf-8")
    assert load_settings() == DEFAULTS


def test_bad_value_is_dropped_without_losing_the_rest():
    ref = [0.7, 0.75, 0.5]
    state_module.SETTINGS_FILE.write_text(json.dumps(
        {"alert_delay": 999, "head_threshold": 0.2, "obsolete": 1, "reference": ref}), encoding="utf-8")
    settings = load_settings()
    assert settings["alert_delay"] == DEFAULTS["alert_delay"]
    assert settings["head_threshold"] == 0.2
    assert settings["reference"] == ref
    assert "obsolete" not in settings


def test_invalid_reference_is_dropped():
    state_module.SETTINGS_FILE.write_text(json.dumps({"reference": [0.7, 0.75, 0]}), encoding="utf-8")
    assert load_settings()["reference"] is None
