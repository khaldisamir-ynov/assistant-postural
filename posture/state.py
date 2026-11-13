"""Etat partage entre les fils (detection, serveur, icone, indicateur) et reglages persistants."""

import json
import logging
import os
import re
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

from posture import core

log = logging.getLogger(__name__)

if sys.platform == "win32":
    APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "AssistantPosture"
else:
    APP_DIR = Path.home() / "Library" / "Application Support" / "AssistantPosture"
SETTINGS_FILE = APP_DIR / "settings.json"

CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")
BOOLEANS = ("enabled", "detect_posture", "detect_head", "detect_lean", "detect_close", "detect_hand",
            "detect_axis", "show_pill")
RANGES = {
    "alert_delay": (1, 60),
    "posture_threshold": (0.01, 0.3),
    "escalation_delay": (5, 600),
    "head_threshold": (0.01, 0.5),
    "lean_angle": (2, 30),
    "close_threshold": (0.05, 1.0),
    "hand_threshold": (0.5, 4.0),
    "axis_threshold": (0.01, 0.3),
}
# Coach : token Hugging Face de l'utilisateur (vide = pas de coach) et organisation facturee facultative
PATTERNS = {"coach_token": r"(hf_[A-Za-z0-9]{30,60})?", "coach_bill_to": r"[A-Za-z0-9_-]{0,64}"}
DEFAULT_PLACE = "Mon poste"
MAX_PLACES, MAX_SCREENS = 10, 4
DEFAULTS = {
    "enabled": True,
    # Une detection par etape (1 : posture affaissee, 2 : penche). Les autres restent disponibles, revalidees une a une.
    "detect_posture": True,
    "posture_threshold": core.POSTURE_THRESHOLD,
    "detect_head": False,
    "head_threshold": core.HEAD_THRESHOLD,
    "detect_lean": True,                      # etape 2
    "lean_angle": core.LEAN_ANGLE,
    "detect_close": False,
    "close_threshold": core.CLOSE_THRESHOLD,
    "detect_hand": False,
    "hand_threshold": core.HAND_THRESHOLD,
    "detect_axis": False,                     # axe tete -> bassin : C1 non atteint au banc
    "axis_threshold": core.AXIS_THRESHOLD,
    "alert_delay": core.ALERT_DELAY_SECONDS,  # avant le halo
    "show_pill": True,
    "escalation_delay": 30,                   # halo -> pastille « Redressez-vous »
    "overlay_corner": "top-right",
    "place": DEFAULT_PLACE,                   # lieu de travail actif (choisi a la main)
    "places": {DEFAULT_PLACE: []},            # lieu -> postures de reference (une par ecran), fixees par la calibration
    "coach_token": "",
    "coach_bill_to": "",
}

# Chaque champ est remplace d'un bloc (jamais modifie en place) : lecture sans verrou depuis les autres fils.
state = SimpleNamespace(settings=dict(DEFAULTS), status={"state": "starting"}, jpeg=None, viewers=0,
                        calib_start=None, calib_samples=[], calib_add=False, calib_message=None,
                        test_alert_until=0.0, running=True,
                        stats=None)  # stats : compteurs du jour (posture.stats)
_lock = threading.RLock()  # reentrant : change_place et save_reference appellent update_settings


def validate(update):
    """Valide des reglages recus de l'interface (frontiere de confiance). Leve ValueError."""
    for key, value in update.items():
        if key in RANGES:
            low, high = RANGES[key]
            ok = isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high
        elif key in BOOLEANS:
            ok = isinstance(value, bool)
        elif key in PATTERNS:
            ok = isinstance(value, str) and re.fullmatch(PATTERNS[key], value) is not None
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
    ref, places, place = data.pop("reference", None), data.pop("places", None), data.pop("place", None)
    if isinstance(places, dict):
        places = {name: [r for r in refs if core.valid_reference(r)][:MAX_SCREENS]
                  for name, refs in list(places.items())[:MAX_PLACES] if valid_place_name(name) and isinstance(refs, list)}
    if places:
        settings["places"] = places
    elif core.valid_reference(ref):
        settings["places"] = {DEFAULT_PLACE: [ref]}  # reglages 0.4 et avant : une seule reference
    settings["place"] = place if place in settings["places"] else next(iter(settings["places"]))
    for key, value in data.items():
        try:
            settings.update(validate({key: value}))
        except ValueError as e:
            log.warning("%s : ignore", e)
    return settings


def valid_place_name(name):
    return isinstance(name, str) and 0 < len(name) <= 30 and name == name.strip() and name.isprintable()


def change_place(action):
    """{"add" | "select" | "delete": nom} venant de l'interface (frontiere de confiance). Leve ValueError."""
    if not (isinstance(action, dict) and len(action) == 1):
        raise ValueError("Action sur le lieu invalide")
    (verb, name), = action.items()
    with _lock:
        places, current = state.settings["places"], state.settings["place"]
        if not valid_place_name(name):
            raise ValueError("Nom de lieu invalide (1 à 30 caractères)")
        if verb == "add" and name not in places and len(places) < MAX_PLACES:
            update = {"places": {**places, name: []}, "place": name}
        elif verb == "select" and name in places:
            update = {"place": name}
        elif verb == "delete" and name in places and len(places) > 1:
            rest = {k: v for k, v in places.items() if k != name}
            update = {"places": rest, "place": current if current != name else next(iter(rest))}
        else:
            raise ValueError(f"Action impossible sur le lieu {name!r}")
        update_settings(update)


def save_reference(reference, add):
    """Calibration du lieu actif : remplace ses references, ou ajoute celle d'un autre ecran."""
    with _lock:
        s = state.settings
        refs = (s["places"][s["place"]] + [reference])[-MAX_SCREENS:] if add else [reference]
        update_settings({"places": {**s["places"], s["place"]: refs}})


def update_settings(update):
    with _lock:
        state.settings = {**state.settings, **update}
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(state.settings, indent=2), encoding="utf-8")
