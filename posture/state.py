"""Etat partage entre les fils (detection, serveur, icone, indicateur) et reglages persistants."""

import json
import logging
import os
import threading
from pathlib import Path
from types import SimpleNamespace

from posture import core

log = logging.getLogger(__name__)

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "AssistantPosture"
SETTINGS_FILE = APP_DIR / "settings.json"

CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")
BOOLEANS = ("enabled", "detect_slouch", "detect_head", "show_pill")
RANGES = {
    "alert_delay": (1, 60),
    "escalation_delay": (5, 600),
    "slouch_threshold": (0.01, 0.4),
    "head_threshold": (0.01, 0.5),
}
DEFAULTS = {
    "enabled": True,
    "detect_slouch": True,
    "detect_head": True,
    "slouch_threshold": core.SLOUCH_THRESHOLD,
    "head_threshold": core.HEAD_THRESHOLD,
    "alert_delay": core.ALERT_DELAY_SECONDS,  # avant le halo
    "show_pill": True,
    "escalation_delay": 30,                   # halo -> pastille « Redressez-vous »
    "overlay_corner": "top-right",
    "reference": None,                        # metriques de la bonne posture, fixees par la calibration
}

# Chaque champ est remplace d'un bloc (jamais modifie en place) : lecture sans verrou depuis les autres fils.
state = SimpleNamespace(settings=dict(DEFAULTS), status={"state": "starting"}, jpeg=None, viewers=0,
                        calib_start=None, calib_samples=[], test_alert_until=0.0, running=True)
_lock = threading.Lock()


def validate(update):
    """Valide des reglages recus de l'interface (frontiere de confiance). Leve ValueError."""
    for key, value in update.items():
        if key in RANGES:
            low, high = RANGES[key]
            ok = isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high
        elif key in BOOLEANS:
            ok = isinstance(value, bool)
        elif key == "overlay_corner":
            ok = value in CORNERS
        else:
            ok = False
        if not ok:
            raise ValueError(f"Reglage invalide : {key}={value!r}")
    return update


def load_settings():
    """Reglages sauvegardes ; une valeur invalide est ignoree sans perdre les autres (ni la calibration)."""
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("format inattendu")
    except FileNotFoundError:
        return dict(DEFAULTS)
    except (OSError, ValueError) as e:
        log.warning("Reglages illisibles (%s), valeurs par defaut", e)
        return dict(DEFAULTS)

    settings = dict(DEFAULTS)
    ref = data.pop("reference", None)
    settings["reference"] = ref if core.valid_reference(ref) else None
    for key, value in data.items():
        try:
            settings.update(validate({key: value}))
        except ValueError as e:
            log.warning("%s : ignore", e)
    return settings


def update_settings(update):
    with _lock:
        state.settings = {**state.settings, **update}
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(state.settings, indent=2), encoding="utf-8")
