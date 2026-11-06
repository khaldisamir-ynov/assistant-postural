import json

import pytest

from posture import state as state_module
from posture.state import DEFAULTS, change_place, load_settings, state, validate


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
    assert settings["places"] == {"Mon poste": [ref]} and settings["place"] == "Mon poste"  # migration 0.4
    assert "obsolete" not in settings


def test_invalid_reference_is_dropped():
    state_module.SETTINGS_FILE.write_text(json.dumps({"reference": [0.7, 0.75, 0]}), encoding="utf-8")
    assert load_settings()["places"] == {"Mon poste": []}


def test_places_are_loaded_and_cleaned():
    ref = [0.7, 0.75, 0.5]
    state_module.SETTINGS_FILE.write_text(json.dumps({
        "places": {"Bureau": [ref, [0, 0, 0]], "Maison": [], "	": [ref], "Bar": "x"}, "place": "Inconnu",
    }), encoding="utf-8")
    settings = load_settings()
    assert settings["places"] == {"Bureau": [ref], "Maison": []}
    assert settings["place"] == "Bureau"


def test_change_place():
    change_place({"add": "Bureau"})
    assert state.settings["place"] == "Bureau" and state.settings["places"]["Bureau"] == []
    change_place({"select": "Mon poste"})
    assert state.settings["place"] == "Mon poste"
    change_place({"delete": "Mon poste"})
    assert list(state.settings["places"]) == ["Bureau"] and state.settings["place"] == "Bureau"
    for bad in ({"delete": "Bureau"}, {"add": "Bureau"}, {"select": "Bar"}, {"add": ""}, {"add": " x"},
                {"add": "a" * 31}, {"add": ["x"]}, {"rename": "Bureau"}, {"add": "a", "select": "b"}, []):
        with pytest.raises(ValueError):
            change_place(bad)
