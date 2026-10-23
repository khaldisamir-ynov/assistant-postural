from posture.core import compute_metrics, deviations, evaluate_posture, valid_reference

REF = compute_metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.50), (0.65, 0.50))


def test_reference_posture_is_ok():
    assert evaluate_posture(REF, REF) == (False, False)


def test_mirror_gives_same_metrics():
    assert compute_metrics((0.55, 0.30), (0.45, 0.30), (0.65, 0.50), (0.35, 0.50)) == REF


def test_slouch_only():
    # epaules et oreilles descendent ensemble de 0.06 (20 % de la largeur d'epaules)
    current = compute_metrics((0.45, 0.36), (0.55, 0.36), (0.35, 0.56), (0.65, 0.56))
    assert evaluate_posture(current, REF) == (True, False)
    assert abs(deviations(current, REF)[0] - 0.2) < 1e-9


def test_head_forward_only():
    current = compute_metrics((0.45, 0.36), (0.55, 0.36), (0.35, 0.50), (0.65, 0.50))
    assert evaluate_posture(current, REF) == (False, True)


def test_valid_reference():
    assert valid_reference(list(REF))
    for bad in (None, [1, 2], [0.5, 0.6, 0], [0.5, -0.1, 0.3], ["a", 1, 1], [True, 1, 1]):
        assert not valid_reference(bad)
