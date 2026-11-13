import json

from posture import state as state_module
from helpers import metrics
from posture.detector import CALIBRATION_SECONDS, update_status
from posture.state import state

TURNED = metrics((0.47, 0.30), (0.53, 0.30), (0.42, 0.50), (0.58, 0.50))  # tourne vers un autre ecran : epaules etroites

# Detections des versions precedentes (desactivees par defaut depuis l'etape 1), testees une a une
OTHERS = {"detect_posture": False, "detect_head": True, "detect_lean": True, "detect_close": True,
          "detect_hand": True}
GOOD = metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.50), (0.65, 0.50))
HEAD_FORWARD = metrics((0.45, 0.36), (0.55, 0.36), (0.35, 0.50), (0.65, 0.50))


def test_calibration_saves_average_reference():
    state.calib_start = 100.0
    assert update_status(GOOD, state.settings, None, 101.0) is None
    assert state.status["state"] == "calibrating"
    update_status(GOOD, state.settings, None, 100.0 + CALIBRATION_SECONDS + 0.1)
    assert state.calib_start is None
    assert state.settings["places"] == {"Mon poste": [list(GOOD)]}
    assert json.loads(state_module.SETTINGS_FILE.read_text(encoding="utf-8"))["places"] == {"Mon poste": [list(GOOD)]}


def test_failed_calibration_keeps_previous_reference():
    state.settings = {**state.settings, "places": {"Mon poste": [[0.5, 0.5, 0.3]]}}
    state.calib_start = 100.0
    update_status(None, state.settings, None, 100.0 + CALIBRATION_SECONDS + 0.1)
    assert state.settings["places"] == {"Mon poste": [[0.5, 0.5, 0.3]]}


def test_alert_only_after_delay_then_clears():
    s = {**state.settings, **OTHERS, "places": {"Mon poste": [list(GOOD)]}, "alert_delay": 2}
    bad_since = update_status(HEAD_FORWARD, s, None, 1000.0)
    assert state.status["state"] == "bad" and state.status["head"]
    bad_since = update_status(HEAD_FORWARD, s, bad_since, 1001.9)
    assert state.status["state"] == "bad"
    bad_since = update_status(HEAD_FORWARD, s, bad_since, 1002.0)
    assert state.status["state"] == "alert" and state.status["alert_since"] == 1002.0
    assert update_status(GOOD, s, bad_since, 1003.0) is None
    assert state.status["state"] == "ok"


def test_disabled_check_never_alerts():
    s = {**state.settings, **OTHERS, "places": {"Mon poste": [list(GOOD)]}, "detect_head": False}
    assert update_status(HEAD_FORWARD, s, None, 1000.0) is None
    assert state.status["state"] == "ok"


def test_absent_and_uncalibrated():
    update_status(GOOD, state.settings, None, 1.0)
    assert state.status["state"] == "uncalibrated"
    update_status(None, {**state.settings, "places": {"Mon poste": [list(GOOD)]}}, 5.0, 6.0)
    assert state.status["state"] == "absent"


def test_hysteresis_keeps_alert_until_clearly_better():
    s = {**state.settings, **OTHERS, "places": {"Mon poste": [list(GOOD)]}, "head_threshold": 0.1}
    # tete un peu en avant : ecart ~0.09, sous le seuil (0.1) mais au-dessus de 80 % du seuil
    slightly = metrics((0.45, 0.318), (0.55, 0.318), (0.35, 0.50), (0.65, 0.50))
    assert update_status(slightly, s, None, 1000.0) is None  # pas encore en mauvaise posture : OK
    bad_since = update_status(HEAD_FORWARD, s, None, 1000.0)
    assert update_status(slightly, s, bad_since, 1001.0) == bad_since  # deja en mauvaise posture : on y reste
    assert update_status(GOOD, s, bad_since, 1002.0) is None


def test_add_screen_and_compare_to_closest_reference(monkeypatch):
    monkeypatch.setattr(state, "calib_add", True)
    state.settings = {**state.settings, "places": {"Mon poste": [list(GOOD)]}}
    state.calib_start = 100.0
    update_status(TURNED, state.settings, None, 100.0 + CALIBRATION_SECONDS + 0.1)
    assert state.settings["places"]["Mon poste"] == [list(GOOD), list(TURNED)]
    update_status(TURNED, state.settings, None, 200.0)  # droit face au 2e ecran : pas d'alerte
    assert state.status["state"] == "ok" and state.status["screen"] == 1
    update_status(HEAD_FORWARD, state.settings, None, 201.0)
    assert state.status["state"] == "bad" and state.status["screen"] == 0


def test_recalibration_replaces_all_screens(monkeypatch):
    monkeypatch.setattr(state, "calib_add", False)
    state.settings = {**state.settings, "places": {"Mon poste": [list(GOOD), list(TURNED)]}}
    state.calib_start = 100.0
    update_status(GOOD, state.settings, None, 100.0 + CALIBRATION_SECONDS + 0.1)
    assert state.settings["places"]["Mon poste"] == [list(GOOD)]


def test_lean_and_close_reasons():
    s = {**state.settings, **OTHERS, "places": {"Mon poste": [list(GOOD)]}}
    update_status(metrics((0.48, 0.30), (0.58, 0.30), (0.35, 0.50), (0.65, 0.50)), s, None, 1.0)  # cou penche ~8.5 deg
    assert state.status["lean"] and not state.status["close"]
    # trop pres : epaules 33 % plus larges ; les ecarts epaules/tete, faussees par la perspective, ne sont pas signales
    update_status(metrics((0.40, 0.33), (0.60, 0.33), (0.30, 0.60), (0.70, 0.60)), s, None, 2.0)
    assert state.status["close"] and not state.status["head"]


def test_calibration_refused_if_moving_and_ignores_first_second():
    state.calib_start = 100.0
    state.calib_samples = [HEAD_FORWARD] * 5 + [GOOD] * 10  # 1er tiers ignore : on lache la souris
    update_status(None, state.settings, None, 100.0 + CALIBRATION_SECONDS + 0.1)
    assert state.settings["places"]["Mon poste"] == [list(GOOD)]
    assert state.calib_message["text"].startswith("Calibration enregistrée")

    moved = metrics((0.45, 0.40), (0.55, 0.40), (0.35, 0.60), (0.65, 0.60))  # 10 cm plus bas
    state.calib_start, state.calib_samples = 200.0, [GOOD, moved] * 6
    update_status(None, state.settings, None, 200.0 + CALIBRATION_SECONDS + 0.1)
    assert "bougé" in state.calib_message["text"]
    assert state.settings["places"]["Mon poste"] == [list(GOOD)]  # reference precedente conservee


def test_hand_on_face_alerts_without_reference_change():
    s = {**state.settings, **OTHERS, "places": {"Mon poste": [list(GOOD)]}}
    update_status(GOOD, s, None, 1.0, hand_dist=1.4)
    assert state.status["state"] == "bad" and state.status["hand"]
    update_status(GOOD, s, None, 2.0, hand_dist=3.0)
    assert state.status["state"] == "ok"
    update_status(GOOD, {**s, "detect_hand": False}, None, 3.0, hand_dist=1.0)
    assert state.status["state"] == "ok"


# --- Etape 1 : posture droite ou affaissee (seule detection active par defaut) ---

SLUMPED = metrics((0.45, 0.33), (0.55, 0.33), (0.35, 0.52), (0.65, 0.52))  # tete et epaules plus bas, cou plus court


def test_step1_slumped_posture_alerts_after_delay():
    s = {**state.settings, "places": {"Mon poste": [list(GOOD)]}}
    # etapes 1 et 2 actives par defaut, les autres detections desactivees
    assert s["detect_posture"] and s["detect_lean"] and not (s["detect_head"] or s["detect_close"]
                                                             or s["detect_hand"])
    update_status(GOOD, s, None, 1.0)
    assert state.status["state"] == "ok" and abs(state.status["posture_dev"]) < 1e-9
    bad_since = update_status(SLUMPED, s, None, 10.0)
    assert state.status["state"] == "bad" and state.status["posture"] and state.status["posture_dev"] > 0.03
    update_status(SLUMPED, s, bad_since, 10.0 + s["alert_delay"])
    assert state.status["state"] == "alert"


def test_step1_camera_shift_is_ignored():
    # toute l'image decalee de 10 % vers le bas (ecran incline) : la hauteur tete-epaules ne change pas
    shifted = metrics((0.45, 0.40), (0.55, 0.40), (0.35, 0.60), (0.65, 0.60))
    update_status(shifted, {**state.settings, "places": {"Mon poste": [list(GOOD)]}}, None, 1.0)
    assert state.status["state"] == "ok"


def test_step1_needs_a_new_calibration():
    s = {**state.settings, "places": {"Mon poste": [list(GOOD[:4])]}}  # reference d'avant l'etape 1
    update_status(GOOD, s, None, 1.0)
    assert state.status["state"] == "uncalibrated"


# --- Etape 2 : penche sur le cote / accoude (axe du cou) ---

def test_step2_leaning_alerts_and_camera_shift_is_ignored():
    s = {**state.settings, "places": {"Mon poste": [list(GOOD)]}}
    update_status(metrics((0.48, 0.30), (0.58, 0.30), (0.35, 0.50), (0.65, 0.50)), s, None, 1.0)  # ~8.5 deg
    assert state.status["state"] == "bad" and state.status["lean"] and state.status["lean_dev"] > s["lean_angle"]
    update_status(metrics((0.46, 0.30), (0.56, 0.30), (0.35, 0.50), (0.65, 0.50)), s, None, 2.0)  # ~2.9 deg : toleree
    assert state.status["state"] == "ok"
    shifted = metrics((0.55, 0.40), (0.65, 0.40), (0.45, 0.60), (0.75, 0.60))  # toute l'image decalee
    update_status(shifted, s, None, 3.0)
    assert state.status["state"] == "ok"


def test_axis_flags_slumped_torso_only_when_enabled():
    from posture.core import compute_metrics
    eyes = (0.47, 0.27), (0.53, 0.27)
    upright = compute_metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.50), (0.65, 0.50), *eyes, (0.4, 1.38), (0.6, 1.38))
    slumped = compute_metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.50), (0.65, 0.50), *eyes, (0.4, 1.32), (0.6, 1.32))
    s = {**state.settings, "places": {"Mon poste": [list(upright)]}, "detect_axis": True}
    update_status(slumped, s, None, 1000.0)
    assert state.status["axis"] and state.status["state"] == "bad"
    update_status(slumped, {**s, "detect_axis": False}, None, 1000.0)
    assert state.status["state"] == "ok"
