import sys
from pathlib import Path

import pytest

from helpers import metrics

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "essais"))
from valider_images import verdict  # noqa: E402

REF = metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.50), (0.65, 0.50))
FAR, NEAR = 3.0, 1.0  # main a 3 ou 1 ecart d'yeux du nez


def test_valid_photos():
    assert verdict("droit", REF, REF, None, set()) is None
    assert verdict("droit2", REF, REF, FAR, set()) is None
    assert verdict("menton_main", REF, REF, NEAR, set()) is None
    assert verdict("telephone", REF, REF, NEAR, {"cell phone"}) is None
    assert verdict("boire", REF, REF, NEAR, {"cup", "person"}) is None


def test_label_not_shown():
    assert verdict("telephone", REF, REF, NEAR, {"cup"}) == "telephone non detecte"
    assert verdict("boire", REF, REF, NEAR, set()) == "boisson non detectee"
    assert verdict("menton_main", REF, REF, FAR, set()) == "main loin du visage"
    assert verdict("menton_main", REF, REF, NEAR, {"cell phone"}) == "telephone ou boisson present"
    assert verdict("droit", REF, REF, NEAR, set()) == "main pres du visage"
    assert verdict("droit", None, None, None, set()) == "tete ou epaules non vues"


def test_witness_rejected_when_edit_moves_the_body():
    shifted = metrics((0.45, 0.33), (0.55, 0.33), (0.35, 0.50), (0.65, 0.50))  # cou raccourci de 15 %
    assert verdict("droit2", shifted, REF, None, set()).startswith("corps deplace")


def test_vlm_answer_parsing():
    pytest.importorskip("openai")  # dependance des seuls essais, absente de l'integration continue
    from comparer_vlm import parse
    assert parse("Téléphone.") == "telephone"
    assert parse("boisson, pas de telephone") == "boisson"
    assert parse("Aucun") == "aucun"
    assert parse("") == "?"


def test_comparison_scores_and_rules():
    pytest.importorskip("openai")
    from comparer_approches import CLASSES, decide, hybrid, scores, wilson
    from comparer_vlm import parse
    assert parse("Trop près de l'écran", CLASSES) == "trop_pres"
    assert parse("Affaissée.", CLASSES) == "affaissee"
    assert wilson(0, 0) == (0.0, 1.0)
    lo, hi = wilson(18, 18)
    assert hi == 1.0 and 0.8 < lo < 0.85  # 18/18 n'exclut pas un vrai taux de 82 %

    a_rows = {1: ("tete_avant", "affaissee"), 2: ("droit2", "affaissee"), 3: ("droit", "correcte"),
              4: ("penche", "penchee")}
    s = scores(list(a_rows.values()))
    assert (s["tp"], s["bad"], s["fp"], s["good"]) == (2, 2, 1, 2)
    # Hybride : le VLM annule la fausse alerte de la photo 2, garde les vraies
    e = hybrid(a_rows, {1: ("tete_avant", "affaissee"), 2: ("droit2", "correcte"), 4: ("penche", "penchee")})
    assert e[2][1] == "correcte" and e[1][1] == "affaissee" and e[4][1] == "penchee"

    a = {**s, "latency": 0.02}
    assert decide(a, a, False) == "reference"
    assert decide({**s, "recall": 0.5, "latency": 1}, a, True).startswith("écartée (C11a")
    assert decide({**s, "latency": 4}, a, True) == "écartée (C11b fausses alertes, C11c latence)"
    good = {**s, "false": 0.0, "latency": 1}
    assert decide(good, a, True).startswith("équivalente")  # intervalles qui se chevauchent : A gardee
    better = {**good, "recall_ci": (0.9, 1), "false_ci": (0, 0.05)}
    worse = {**a, "recall_ci": (0.1, 0.5), "false_ci": (0.3, 0.6)}
    assert decide(better, worse, True) == "option désactivée par défaut (C11d)"
    assert decide(better, worse, False) == "meilleure que A"


def test_bust_points_follow_the_torso():
    import numpy as np
    from reperes_buste import follow, measures
    rng = np.random.default_rng(0)
    img = (rng.random((240, 320)) * 255).astype(np.uint8)
    img = __import__("cv2").GaussianBlur(img, (5, 5), 0)
    moved = np.roll(img, 3, axis=0)  # tout le buste descend de 3 px
    pts = np.array([[160.0, 150.0], [140.0, 170.0], [np.nan, np.nan]], np.float32)
    out = follow(img, moved, pts)
    assert np.isnan(out[2, 0])  # un repere perdu le reste
    assert np.allclose(out[:2, 1], pts[:2, 1] + 3, atol=0.3)
    # front et epaules immobiles, buste qui remonte de 10 px vers le front : la ligne front -> buste raccourcit
    ref = (np.array([160.0, 40.0]), np.array([160.0, 120.0]), 100.0)
    ref_pts = np.array([[150.0, 180.0], [170.0, 180.0]])
    m = measures(ref, ref, ref_pts, ref_pts - [0, 10], np.array([True, True]))
    assert m["a"] > 0.05 and m["c"] < 0


def test_stickers_found_by_color_on_the_chest():
    import cv2
    import numpy as np
    from types import SimpleNamespace
    from reperes_buste import stickers
    img = np.full((480, 640, 3), 90, np.uint8)
    pts = [SimpleNamespace(x=0.5, y=0.5, visibility=0.0) for _ in range(33)]
    for i, (x, y) in {2: (0.47, 0.25), 5: (0.53, 0.25), 11: (0.65, 0.55), 12: (0.35, 0.55)}.items():
        pts[i] = SimpleNamespace(x=x, y=y, visibility=1.0)
    cv2.circle(img, (320, 330), 9, (0, 255, 0), -1)  # gommette verte du haut
    cv2.circle(img, (325, 400), 9, (0, 255, 0), -1)  # gommette verte du bas
    cv2.circle(img, (40, 400), 9, (0, 255, 0), -1)   # objet vert hors du buste : ignore
    found = stickers(img, pts, "vert")
    assert len(found) == 2 and found[0][1] < found[1][1]
    assert abs(found[0][0] - 320) < 2 and abs(found[1][1] - 400) < 2
