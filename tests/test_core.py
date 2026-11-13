import math

from helpers import metrics
from posture.core import deviations, evaluate_posture, hand_face_distance, valid_reference

REF = metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.50), (0.65, 0.50))


def test_reference_posture_is_ok():
    assert evaluate_posture(REF, REF) == (False, False)


def test_mirror_gives_same_metrics():
    assert metrics((0.55, 0.30), (0.45, 0.30), (0.65, 0.50), (0.35, 0.50)) == REF


def test_slouch_only():
    # epaules et oreilles descendent ensemble de 0.06 (20 % de la largeur d'epaules)
    current = metrics((0.45, 0.36), (0.55, 0.36), (0.35, 0.56), (0.65, 0.56))
    assert evaluate_posture(current, REF) == (True, False)
    assert abs(deviations(current, REF)[0] - 0.2) < 1e-9


def test_head_forward_only():
    current = metrics((0.45, 0.36), (0.55, 0.36), (0.35, 0.50), (0.65, 0.50))
    assert evaluate_posture(current, REF) == (False, True)


def test_valid_reference():
    assert valid_reference(list(REF))
    for bad in (None, [1, 2], [0.5, 0.6, 0], [0.5, -0.1, 0.3], ["a", 1, 1], [True, 1, 1]):
        assert not valid_reference(bad)


def test_lean_and_close():
    leaning = metrics((0.48, 0.30), (0.58, 0.30), (0.35, 0.50), (0.65, 0.50))  # tete decalee de 0.03 sur le cote
    assert abs(deviations(leaning, REF)[2] - math.degrees(math.atan2(0.03, 0.2))) < 1e-9
    close = metrics((0.40, 0.25), (0.60, 0.25), (0.30, 0.55), (0.70, 0.55))
    assert abs(deviations(close, REF)[3] - 1 / 3) < 1e-9


def test_old_three_number_reference_has_no_lean():
    leaning = metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.47), (0.65, 0.53))
    assert deviations(leaning, list(REF[:3]))[2] == 0.0


def test_hand_face_distance():
    from types import SimpleNamespace as P
    lm = [P(x=0.5, y=0.5, visibility=0.0) for _ in range(33)]
    lm[0], lm[2], lm[5] = P(x=0.50, y=0.30, visibility=1), P(x=0.47, y=0.27, visibility=1), P(x=0.53, y=0.27, visibility=1)
    assert hand_face_distance(lm) is None  # aucune main visible
    lm[15] = P(x=0.50, y=0.39, visibility=1)  # poignet sous le menton, a 1.5 ecart d'yeux du nez
    assert abs(hand_face_distance(lm) - 1.5) < 1e-9
    lm[0] = P(x=0.50, y=0.30, visibility=0.1)
    assert hand_face_distance(lm) is None  # visage invisible


def test_axis_head_to_hips():
    from posture.core import axis_shortening, compute_metrics
    eyes = (0.47, 0.27), (0.53, 0.27)  # haut de la tete estime a 0.27 - 1.5 * 0.06 = 0.18
    upright = compute_metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.50), (0.65, 0.50), *eyes, (0.4, 1.38), (0.6, 1.38))
    assert abs(upright[5] - 1.2 / 0.3) < 1e-9  # 1.2 de long pour 0.3 de largeur d'epaules
    assert valid_reference(list(upright))
    slumped = compute_metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.50), (0.65, 0.50), *eyes, (0.4, 1.32), (0.6, 1.32))
    assert abs(axis_shortening(slumped, upright) - 0.05) < 1e-9
    assert axis_shortening(slumped, upright[:5]) == 0.0  # calibration d'avant l'axe : pas de mesure
