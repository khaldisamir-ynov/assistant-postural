"""Statistiques du jour : de simples compteurs (secondes, nombre d'alertes), aucune image."""

import json
import logging

from posture.state import APP_DIR

log = logging.getLogger(__name__)

STATS_FILE = APP_DIR / "stats.json"
TRACKED = ("ok", "bad", "alert")  # personne presente et calibree
REASONS = ("posture", "slouch", "head", "lean", "close", "hand")


def empty(day):
    return {"date": day, "good": 0.0, "bad": 0.0, "posture": 0.0, "slouch": 0.0, "head": 0.0, "lean": 0.0, "close": 0.0, "hand": 0.0, "alerts": 0}


def record(stats, prev_state, status, dt, day):
    """Ajoute dt secondes de l'etat courant. Retourne un nouveau dict (lu sans verrou par le serveur)."""
    stats = dict(stats) if stats and stats["date"] == day else empty(day)  # nouveau jour : remise a zero
    state = status.get("state")
    if state in TRACKED:
        stats["good" if state == "ok" else "bad"] += dt
        for reason in REASONS:
            stats[reason] += dt if status.get(reason) else 0
        stats["alerts"] += state == "alert" and prev_state != "alert"
    return stats


def load(day):
    """Compteurs du jour sauvegardes, ou des compteurs vides (autre jour, fichier absent ou abime)."""
    try:
        data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = {**empty(day), **data}  # fichier d'une version precedente : nouveaux compteurs a zero
        ok = (isinstance(data, dict) and data.keys() == empty(day).keys() and data["date"] == day
              and all(isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0
                      for k, v in data.items() if k != "date"))
        if ok:
            return data
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        log.warning("Statistiques illisibles (%s), remise a zero", e)
    return empty(day)


def save(stats):
    if stats:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(json.dumps(stats), encoding="utf-8")
