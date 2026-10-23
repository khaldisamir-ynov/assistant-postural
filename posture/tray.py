"""Icone de la zone de notification : sa couleur suit la posture, clic droit pour les actions rapides."""

import threading
import time
import webbrowser

import pystray
from PIL import Image, ImageDraw

from posture import autostart
from posture.server import URL
from posture.state import state, update_settings

GREEN, AMBER, BLUE, GREY, RED = "#1f9d55", "#f0a030", "#3b5bdb", "#98a2b3", "#d64545"
STATES = {  # etat -> (couleur, libelle)
    "starting": (GREY, "Démarrage…"),
    "ok": (GREEN, "Posture correcte"),
    "bad": (GREEN, "Posture correcte"),  # pas de signal avant le delai d'alerte
    "alert": (AMBER, "Redressez-vous"),
    "calibrating": (BLUE, "Calibration…"),
    "uncalibrated": (AMBER, "Calibration nécessaire"),
    "absent": (GREY, "Hors champ"),
    "paused": (GREY, "En pause"),
    "camera_error": (RED, "Webcam indisponible"),
    "error": (RED, "Erreur, voir le journal"),
}


def draw_icon(color):
    """Silhouette blanche (tete + epaules) sur une pastille de couleur."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill=color)
    d.ellipse((23, 12, 41, 30), fill="white")
    d.pieslice((13, 34, 51, 70), 180, 360, fill="white")
    return img


def _toggle_pause(icon):
    update_settings({"enabled": not state.settings["enabled"]})
    icon.update_menu()


def _toggle_autostart(icon):
    autostart.set_enabled(not autostart.is_enabled())
    icon.update_menu()


def _follow_status(icon):
    icon.visible = True
    shown = None
    while state.running:
        current = (state.status.get("state", "starting"), state.settings["enabled"], autostart.is_enabled())
        if current != shown:
            if shown is None or current[0] != shown[0]:
                color, label = STATES.get(current[0], STATES["starting"])
                icon.icon = draw_icon(color)
                icon.title = f"Assistant de posture : {label}"
            icon.update_menu()  # coches « Pause » / « Démarrage » modifiables depuis l'interface web
            shown = current
        time.sleep(0.5)


def start():
    icon = pystray.Icon("AssistantPosture", draw_icon(GREY), "Assistant de posture", menu=pystray.Menu(
        pystray.MenuItem("Ouvrir les réglages", lambda: webbrowser.open(URL), default=True),
        pystray.MenuItem("Pause", _toggle_pause, checked=lambda item: not state.settings["enabled"]),
        pystray.MenuItem("Lancer au démarrage de Windows", _toggle_autostart,
                         checked=lambda item: autostart.is_enabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quitter", lambda: setattr(state, "running", False)),
    ))
    threading.Thread(target=icon.run, kwargs={"setup": _follow_status}, daemon=True, name="tray").start()
    return icon
