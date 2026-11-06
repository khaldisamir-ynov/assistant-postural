import json

from posture import stats as stats_module
from posture.stats import empty, load, record, save

DAY = "2026-10-30"


def test_record_counts_time_and_alert_transitions():
    st = record(None, "starting", {"state": "ok"}, 0.1, DAY)
    st = record(st, "ok", {"state": "bad", "head": True}, 0.1, DAY)
    st = record(st, "bad", {"state": "alert", "head": True, "slouch": True}, 0.1, DAY)
    st = record(st, "alert", {"state": "alert", "head": True}, 0.1, DAY)  # meme alerte : pas recomptee
    st = record(st, "alert", {"state": "absent"}, 0.1, DAY)                # hors champ : non compte
    assert st["alerts"] == 1
    assert round(st["good"], 3) == 0.1 and round(st["bad"], 3) == 0.3
    assert round(st["head"], 3) == 0.3 and round(st["slouch"], 3) == 0.1


def test_new_day_resets_counters():
    st = {**empty(DAY), "good": 100.0, "alerts": 3}
    assert record(st, "ok", {"state": "ok"}, 1.0, "2026-10-31") == {**empty("2026-10-31"), "good": 1.0}


def test_load_roundtrip_and_tolerance():
    st = {**empty(DAY), "good": 12.5, "alerts": 2}
    save(st)
    assert load(DAY) == st
    assert load("2026-10-31") == empty("2026-10-31")  # fichier d'un autre jour
    stats_module.STATS_FILE.write_text(json.dumps({**st, "alerts": -1}), encoding="utf-8")
    assert load(DAY) == empty(DAY)
    stats_module.STATS_FILE.write_text("{abime", encoding="utf-8")
    assert load(DAY) == empty(DAY)
