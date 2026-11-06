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


def test_rejected_token_gives_readable_error(monkeypatch):
    def fake_urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO())

    monkeypatch.setattr(coach.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="Token refusé"):
        coach.ask(STATS, "hf_" + "a" * 34)
