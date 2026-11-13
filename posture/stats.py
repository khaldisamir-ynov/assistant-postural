"""Statistiques : de simples compteurs (secondes, nombre d'alertes), aucune image.

Le jour en cours (stats.json) et un historique des derniers jours (historique.json), chaque jour avec son deroule
par demi-heure (secondes en bonne et en mauvaise posture), pour le bilan du coach.
"""

import json
import logging
import re

from posture.state import APP_DIR

log = logging.getLogger(__name__)

STATS_FILE = APP_DIR / "stats.json"
HISTORY_FILE = APP_DIR / "historique.json"
TRACKED = ("ok", "bad", "alert")  # personne presente et calibree
# « slouch » (epaules, retire le 2026-11-13) reste dans les compteurs : sinon les fichiers deja ecrits seraient rejetes
REASONS = ("posture", "head", "lean", "close", "hand", "axis")
SLOT_MINUTES = 30
HISTORY_DAYS = 30  # au-dela, les jours les plus anciens sont oublies


def empty(day):
    return {"date": day, "good": 0.0, "bad": 0.0, "posture": 0.0, "slouch": 0.0, "head": 0.0, "lean": 0.0, "close": 0.0,
            "hand": 0.0, "axis": 0.0, "alerts": 0, "slots": {}}


def slot_of(hour, minute):
    """Debut de la demi-heure, ex. 14 h 47 -> « 14:30 »."""
    return f"{hour:02d}:{minute - minute % SLOT_MINUTES:02d}"


def record(stats, prev_state, status, dt, day, slot=None):
    """Ajoute dt secondes de l'etat courant. Retourne un nouveau dict (lu sans verrou par le serveur)."""
    stats = dict(stats) if stats and stats["date"] == day else empty(day)  # nouveau jour : remise a zero
    state = status.get("state")
    if state in TRACKED:
        good = state == "ok"
        stats["good" if good else "bad"] += dt
        for reason in REASONS:
            stats[reason] += dt if status.get(reason) else 0
        stats["alerts"] += state == "alert" and prev_state != "alert"
        if slot:
            g, b = stats["slots"].get(slot, (0.0, 0.0))
            stats["slots"] = {**stats["slots"], slot: [g + dt * good, b + dt * (not good)]}
    return stats


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0


def _valid(data, day):
    """Compteurs d'un jour complets et plausibles (fichier modifie a la main ou abime : rejete)."""
    return (isinstance(data, dict) and data.keys() == empty(day).keys() and data["date"] == day
            and all(_number(v) for k, v in data.items() if k not in ("date", "slots"))
            and isinstance(data["slots"], dict)
            and all(re.fullmatch(r"\d\d:\d\d", k) and isinstance(v, list) and len(v) == 2 and all(map(_number, v))
                    for k, v in data["slots"].items()))


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        log.warning("%s illisible (%s), ignore", path.name, e)
        return None


def load(day):
    """Compteurs du jour sauvegardes, ou des compteurs vides (autre jour, fichier absent ou abime)."""
    data = _read(STATS_FILE)
    if isinstance(data, dict):
        data = {**empty(day), **data}  # fichier d'une version precedente : nouveaux compteurs a zero
    return data if _valid(data, day) else empty(day)


def history():
    """Jours sauvegardes valides : {date: compteurs}."""
    data = _read(HISTORY_FILE)
    if not isinstance(data, dict):
        return {}
    return {day: {**empty(day), **st} for day, st in data.items()
            if isinstance(st, dict) and _valid({**empty(day), **st}, day)}


def save(stats):
    """Jour en cours, et sa copie dans l'historique (les HISTORY_DAYS jours les plus recents)."""
    if stats:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(json.dumps(stats), encoding="utf-8")
        days = {**history(), stats["date"]: stats}
        keep = dict(sorted(days.items())[-HISTORY_DAYS:])  # dates ISO : l'ordre alphabetique est chronologique
        HISTORY_FILE.write_text(json.dumps(keep), encoding="utf-8")


def last_days(today_stats, n=7):
    """Resume des n derniers jours suivis, du plus ancien au plus recent, jour en cours compris."""
    days = history()
    if today_stats:
        days[today_stats["date"]] = today_stats
    out = []
    for day, st in sorted(days.items())[-n:]:
        tracked = st["good"] + st["bad"]
        if tracked:
            out.append({"date": day, "minutes": round(tracked / 60), "good_pct": round(100 * st["good"] / tracked),
                        "alerts": st["alerts"]})
    return out
