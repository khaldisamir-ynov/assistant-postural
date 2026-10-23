"""Icone de la zone de notification (Windows) ou de la barre des menus (macOS) : sa couleur suit la posture."""

import sys
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

_shown = None


def draw_icon(color):
    """Silhouette blanche (tete + epaules) sur une pastille de couleur."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill=color)
    d.ellipse((23, 12, 41, 30), fill="white")
    d.pieslice((13, 34, 51, 70), 180, 360, fill="white")
    return img


def start():
    """Cree l'icone. A appeler depuis le fil principal, apres la creation de la fenetre Tk."""
    options = {}
    if sys.platform == "darwin":
        from AppKit import NSApplication
        options["darwin_nsapplication"] = NSApplication.sharedApplication()  # celle de Tk : une seule boucle Cocoa
    icon = pystray.Icon("AssistantPosture", draw_icon(GREY), "Assistant de posture", menu=pystray.Menu(
        pystray.MenuItem("Ouvrir les réglages", lambda: webbrowser.open(URL), default=True),
        pystray.MenuItem("Pause", lambda: update_settings({"enabled": not state.settings["enabled"]}),
                         checked=lambda item: not state.settings["enabled"]),
        pystray.MenuItem("Lancer à l'ouverture de session", lambda: autostart.set_enabled(not autostart.is_enabled()),
                         checked=lambda item: autostart.is_enabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quitter", lambda: setattr(state, "running", False)),
    ), **options)
    # Windows : boucle dans un fil dedie ; macOS : la boucle de Tk sert aussi l'icone
    icon.run_detached(setup=lambda icon: None)
    return icon


def refresh(icon):
    """Suit l'etat de l'application. Appelee depuis le fil principal (obligatoire sous macOS pour AppKit)."""
    global _shown
    current = (state.status.get("state", "starting"), state.settings["enabled"], autostart.is_enabled())
    if current == _shown:
        return
    if _shown is None:
        icon.visible = True
    if _shown is None or current[0] != _shown[0]:
        color, label = STATES.get(current[0], STATES["starting"])
        icon.icon = draw_icon(color)
        icon.title = f"Assistant de posture : {label}"
    icon.update_menu()  # coches « Pause » / « Ouverture de session » modifiables depuis l'interface web
    _shown = current
