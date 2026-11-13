import io
import json
import urllib.error

import pytest

from posture import coach
from posture.stats import empty

STATS = {**empty("2026-10-30"), "good": 1800.0, "bad": 1200.0, "head": 900.0, "alerts": 4}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_sends_only_figures_and_bills_org(monkeypatch):
    sent = {}

    def fake_urlopen(req, timeout):
        sent["req"] = req
        return FakeResponse(json.dumps({"choices": [{"message": {"content": " 1. Conseil \n"}}]}).encode())

    monkeypatch.setattr(coach.urllib.request, "urlopen", fake_urlopen)
    assert coach.ask(STATS, "hf_" + "a" * 34, "ynov") == "1. Conseil"
    req = sent["req"]
    assert req.full_url == coach.URL
    assert req.get_header("X-hf-bill-to") == "ynov"
    assert req.get_header("User-agent").startswith("assistant-posture/")
    assert req.get_header("Authorization") == "Bearer hf_" + "a" * 34
    prompt = json.loads(req.data)["messages"][1]["content"]
    assert '"bonne_posture_pct": 60' in prompt and '"minutes_tete_en_avant": 15' in prompt
    assert "## Postures a surveiller" in prompt and "## Conseils" in prompt  # titres que la page met en forme


def test_summary_adds_half_hours_and_previous_days_as_figures_only():
    st = {**STATS, "slots": {"16:30": [600.0, 1200.0], "09:00": [1500.0, 0.0], "12:00": [60.0, 60.0]}}
    days = [{"date": "2026-10-29", "minutes": 300, "good_pct": 80, "alerts": 2},
            {"date": "2026-10-30", "minutes": 50, "good_pct": 60, "alerts": 4}]  # le jour en cours : deja dans les totaux
    s = coach.summary(st, days)
    assert s["par_demi_heure"] == [{"debut": "09:00", "minutes_suivies": 25, "bonne_posture_pct": 100},
                                   {"debut": "16:30", "minutes_suivies": 30, "bonne_posture_pct": 33}]  # 12:00 : 2 min, trop peu
    assert s["jours_precedents"] == [{"date": "2026-10-29", "minutes_suivies": 300, "bonne_posture_pct": 80,
                                      "alertes": 2}]
    assert coach.summary(STATS)["jours_precedents"] == []


def test_rejected_token_gives_readable_error(monkeypatch):
    def fake_urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO())

    monkeypatch.setattr(coach.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="Token refusé"):
        coach.ask(STATS, "hf_" + "a" * 34)
