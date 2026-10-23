import json

from posture import state as state_module
from posture.core import compute_metrics
from posture.detector import CALIBRATION_SECONDS, update_status
from posture.state import state

GOOD = compute_metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.50), (0.65, 0.50))
HEAD_FORWARD = compute_metrics((0.45, 0.36), (0.55, 0.36), (0.35, 0.50), (0.65, 0.50))


def test_calibration_saves_average_reference():
    state.calib_start = 100.0
    assert update_status(GOOD, state.settings, None, 101.0) is None
    assert state.status["state"] == "calibrating"
    update_status(GOOD, state.settings, None, 100.0 + CALIBRATION_SECONDS + 0.1)
    assert state.calib_start is None
    assert state.settings["reference"] == list(GOOD)
    assert json.loads(state_module.SETTINGS_FILE.read_text(encoding="utf-8"))["reference"] == list(GOOD)


def test_failed_calibration_keeps_previous_reference():
    state.settings = {**state.settings, "reference": [0.5, 0.5, 0.3]}
    state.calib_start = 100.0
    update_status(None, state.settings, None, 100.0 + CALIBRATION_SECONDS + 0.1)
    assert state.settings["reference"] == [0.5, 0.5, 0.3]


def test_alert_only_after_delay_then_clears():
    s = {**state.settings, "reference": list(GOOD), "alert_delay": 2}
    bad_since = update_status(HEAD_FORWARD, s, None, 1000.0)
    assert state.status["state"] == "bad" and state.status["head"]
    bad_since = update_status(HEAD_FORWARD, s, bad_since, 1001.9)
    assert state.status["state"] == "bad"
    bad_since = update_status(HEAD_FORWARD, s, bad_since, 1002.0)
    assert state.status["state"] == "alert" and state.status["alert_since"] == 1002.0
    assert update_status(GOOD, s, bad_since, 1003.0) is None
    assert state.status["state"] == "ok"


def test_disabled_check_never_alerts():
    s = {**state.settings, "reference": list(GOOD), "detect_head": False}
    assert update_status(HEAD_FORWARD, s, None, 1000.0) is None
    assert state.status["state"] == "ok"


def test_absent_and_uncalibrated():
    update_status(GOOD, state.settings, None, 1.0)
    assert state.status["state"] == "uncalibrated"
    update_status(None, {**state.settings, "reference": list(GOOD)}, 5.0, 6.0)
    assert state.status["state"] == "absent"
