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
