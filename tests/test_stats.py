import json

from posture import stats as stats_module
from posture.stats import empty, load, record, save

DAY = "2026-10-30"


def test_record_counts_time_and_alert_transitions():
    st = record(None, "starting", {"state": "ok"}, 0.1, DAY)
    st = record(st, "ok", {"state": "bad", "head": True}, 0.1, DAY)
    st = record(st, "bad", {"state": "alert", "head": True, "lean": True}, 0.1, DAY)
    st = record(st, "alert", {"state": "alert", "head": True}, 0.1, DAY)  # meme alerte : pas recomptee
    st = record(st, "alert", {"state": "absent"}, 0.1, DAY)                # hors champ : non compte
    assert st["alerts"] == 1
    assert round(st["good"], 3) == 0.1 and round(st["bad"], 3) == 0.3
    assert round(st["head"], 3) == 0.3 and round(st["lean"], 3) == 0.1


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


def test_time_is_split_by_half_hour():
    from posture.stats import slot_of
    assert slot_of(14, 47) == "14:30" and slot_of(9, 5) == "09:00"
    st = record(None, "starting", {"state": "ok"}, 1.0, DAY, "14:00")
    st = record(st, "ok", {"state": "bad", "head": True}, 2.0, DAY, "14:00")
    st = record(st, "bad", {"state": "ok"}, 3.0, DAY, "14:30")
    st = record(st, "ok", {"state": "absent"}, 5.0, DAY, "14:30")  # hors champ : non compte
    assert st["slots"] == {"14:00": [1.0, 2.0], "14:30": [3.0, 0.0]}
    save(st)
    assert load(DAY) == st


def test_history_keeps_past_days_and_drops_bad_entries():
    from posture.stats import HISTORY_DAYS, history, last_days
    from datetime import date, timedelta
    for n in range(HISTORY_DAYS + 2):  # plus de jours que la limite, du 1er au 32e jour
        day = (date(2026, 9, 1) + timedelta(days=n)).isoformat()
        save({**empty(day), "good": 60.0 * (n + 1), "bad": 60.0, "alerts": n})
    days = history()
    assert len(days) == HISTORY_DAYS and min(days) == "2026-09-03"  # les plus anciens sont oublies
    data = json.loads(stats_module.HISTORY_FILE.read_text(encoding="utf-8"))
    data["2026-09-10"]["good"] = -5  # entree abimee : ignoree, les autres restent
    stats_module.HISTORY_FILE.write_text(json.dumps(data), encoding="utf-8")
    assert "2026-09-10" not in history() and "2026-09-11" in history()
    today = {**empty("2026-10-05"), "good": 90.0, "bad": 30.0, "alerts": 1}
    week = last_days(today)
    assert len(week) == 7 and week[-1] == {"date": "2026-10-05", "minutes": 2, "good_pct": 75, "alerts": 1}


def test_old_stats_file_without_slots_is_kept():
    old = {k: v for k, v in {**empty(DAY), "good": 12.0}.items() if k != "slots"}  # version 0.4.0
    stats_module.STATS_FILE.write_text(json.dumps(old), encoding="utf-8")
    assert load(DAY) == {**empty(DAY), "good": 12.0}
