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


# Rapport calcule sur le poste (criteres C16, SPECIFICATIONS.md § 4.11)
DAY = {**empty("2026-11-20"), "good": 14400.0, "bad": 4320.0, "head": 2700.0, "lean": 900.0, "hand": 30.0,
       "alerts": 12, "slots": {"09:00": [1700.0, 100.0], "14:00": [1500.0, 300.0], "16:30": [700.0, 1100.0],
                               "17:00": [100.0, 100.0]}}  # 17:00 : moins de 5 min suivies
BEFORE = [{"date": "2026-11-18", "minutes": 300, "good_pct": 70, "alerts": 9},
          {"date": "2026-11-19", "minutes": 280, "good_pct": 74, "alerts": 7}]


def sections(text):
    out, current = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            current = out.setdefault(line[3:], [])
        else:
            current.append(line)
    return out


def test_local_report_has_the_four_sections_in_order():  # C16a
    assert list(sections(coach.local_report(DAY, BEFORE))) == [
        "Bilan", "Postures à surveiller", "Moments de la journée", "Conseils"]


def test_local_report_summary_and_comparison():  # C16b
    bilan = sections(coach.local_report(DAY, BEFORE))["Bilan"]
    assert bilan == ["Temps suivi aujourd'hui : 5 h 12, dont 77 % en bonne posture ; 12 alertes.",
                     "C'est mieux que vos 2 jours précédents (72 % en moyenne)."]
    close = [{**BEFORE[0], "good_pct": 75}]  # 77 contre 75 : moins de 3 points d'ecart
    assert "C'est comparable à votre jour précédent (75 %)." in coach.local_report(DAY, close)
    assert "moins bien que" in coach.local_report(DAY, [{**BEFORE[0], "good_pct": 80}])
    assert "Pas encore de jour précédent" in coach.local_report(DAY)
    # 22 s suivies (cas vu en lancant l'application) : pas de comparaison, temps affiche sans « 0 min »
    short = sections(coach.local_report({**empty("2026-11-20"), "good": 22.0}, BEFORE))["Bilan"]
    assert short == ["Temps suivi aujourd'hui : moins d'une minute, dont 100 % en bonne posture ; 0 alerte.",
                     "Moins de 5 minutes suivies : trop peu pour comparer avec les jours précédents."]


def test_local_report_lists_bad_postures_of_one_minute_or_more():  # C16c
    assert sections(coach.local_report(DAY))["Postures à surveiller"] == [
        "- Tête en avant : 45 min (14 % du temps suivi)", "- Penché sur le côté : 15 min (5 % du temps suivi)"]
    good_day = {**empty("2026-11-20"), "good": 600.0}
    assert sections(coach.local_report(good_day))["Postures à surveiller"] == [
        "- Aucune mauvaise posture d'au moins une minute."]


def test_local_report_moments_use_half_hours_of_five_minutes():  # C16d
    assert sections(coach.local_report(DAY))["Moments de la journée"] == [
        "- Meilleur moment : 09:00-09:30, 94 % en bonne posture.",
        "- Moment le plus difficile : 16:30-17:00, 39 % en bonne posture."]
    tie = {**DAY, "slots": {"10:00": [900.0, 900.0], "11:30": [900.0, 900.0], "23:30": [1800.0, 0.0]}}
    assert sections(coach.local_report(tie))["Moments de la journée"] == [
        "- Meilleur moment : 23:30-00:00, 100 % en bonne posture.",
        "- Moment le plus difficile : 10:00-10:30, 50 % en bonne posture."]  # egalite : le plus tot
    one = {**DAY, "slots": {"09:00": [1700.0, 100.0]}}
    assert sections(coach.local_report(one))["Moments de la journée"] == [
        "- Une seule demi-heure suivie assez longtemps : 09:00-09:30, 94 % en bonne posture."]
    assert "Pas encore de demi-heure" in coach.local_report({**DAY, "slots": {}})


def tips(day, days=()):
    return [line[2:] for line in sections(coach.local_report(day, days))["Conseils"]]


def test_local_report_gives_three_to_five_distinct_tips_from_the_table():  # C16e
    pause = coach.PAUSE.format(debut="16:30")
    table = {tip for pair in coach.ADVICE.values() for tip in pair} | set(coach.GENERAL) | {coach.GOOD_DAY, pause}
    for day in (DAY, {**DAY, "close": 3000.0, "head": 2900.0}, {**empty("2026-11-20"), "good": 600.0}):
        got = tips(day)
        assert 3 <= len(got) <= 5 and len(set(got)) == len(got)
        assert set(got) <= table, got
    assert tips(DAY) == [coach.ADVICE["head"][0], pause, coach.ADVICE["lean"][0], coach.ADVICE["head"][1]]
    every = {**DAY, **{k: 600.0 for k in coach.LABELS}}  # toutes les postures : on s'arrete a 5
    assert len(tips(every)) == 5


def test_local_report_tips_follow_the_figures():  # C16e
    # 2 h 30 d'affilee, chaque demi-heure suivie au moins 28 min : conseil de pause date, sans doublon general
    streak = {**empty("2026-11-20"), "good": 9000.0,
              "slots": {f"{h:02d}:{m:02d}": [1700.0, 0.0] for h, m in ((9, 0), (9, 30), (10, 0), (10, 30), (11, 0))}}
    got = tips(streak)
    assert coach.STREAK.format(debut="09:00", fin="11:30", duree="2 h 30") in got and coach.GENERAL[0] not in got
    assert not any("presque sans pause" in t for t in tips({**streak, "slots": {**streak["slots"], "10:00": [1500.0, 0.0]}}))
    # Alertes frequentes : 10 en 1 h
    noisy = {**empty("2026-11-20"), "good": 3000.0, "bad": 600.0, "head": 600.0, "alerts": 10}
    assert coach.ALERTS.format(n=10) in tips(noisy)
    assert not any("alertes par heure" in t for t in tips({**noisy, "alerts": 5}))
    # Moins bien que d'habitude : recalibrer remonte en tete des conseils generaux
    assert tips(DAY, [{**BEFORE[0], "good_pct": 90}])[3] == coach.GENERAL[1]
    # Tres bonne journee, mais pas apres quelques secondes
    assert tips({**empty("2026-11-20"), "good": 600.0})[0] == coach.GOOD_DAY
    assert coach.GOOD_DAY not in tips({**empty("2026-11-20"), "good": 22.0})


def test_local_report_is_deterministic_and_offline(monkeypatch):  # C16f
    def no_network(*args, **kwargs):
        raise AssertionError("appel reseau")

    monkeypatch.setattr(coach.urllib.request, "urlopen", no_network)
    assert coach.local_report(DAY, BEFORE) == coach.local_report(dict(DAY), list(BEFORE))
