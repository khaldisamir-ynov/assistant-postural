"""Point d'entree : python -m posture, assistant-posture (apres pip install), AssistantPosture.exe ou .app."""

import ctypes
import logging
import signal
import sys
import threading
import webbrowser
from logging.handlers import RotatingFileHandler

from posture import __version__, detector, server, tray
from posture.overlay import Overlay
from posture.state import APP_DIR, load_settings, state

log = logging.getLogger("posture")


def main():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    # Sans console (pythonw / exe) : tout passe par un journal tournant
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s",
                        handlers=[RotatingFileHandler(APP_DIR / "posture.log", maxBytes=1_000_000,
                                                      backupCount=3, encoding="utf-8")])
    threading.excepthook = lambda a: log.error("Erreur dans %s", a.thread.name,
                                               exc_info=(a.exc_type, a.exc_value, a.exc_traceback))
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # texte net sur les ecrans mis a l'echelle
    except (AttributeError, OSError):
        pass

    try:
        httpd = server.Server((server.HOST, server.PORT), server.Handler)
    except OSError:
        # Deja lance (ex. demarrage auto + lancement manuel) : on affiche simplement l'interface existante
        log.info("Instance deja active, ouverture de l'interface")
        webbrowser.open(server.URL)
        return

    log.info("Demarrage v%s, reglages dans %s", __version__, APP_DIR)
    state.settings = load_settings()
    if sys.platform == "darwin":
        import cv2
        # macOS : OpenCV ne peut demander l'autorisation camera que depuis le fil principal, avant la detection
        cv2.VideoCapture(0).release()
    threading.Thread(target=httpd.serve_forever, daemon=True, name="server").start()
    detection = threading.Thread(target=detector.run, name="detection")
    detection.start()
    signal.signal(signal.SIGINT, lambda *_: setattr(state, "running", False))

    overlay = Overlay()  # avant l'icone : sous macOS, c'est Tk qui cree l'application Cocoa
    overlay.root.report_callback_exception = lambda *exc: log.error("Erreur d'affichage", exc_info=exc)
    icon = tray.start()

    def follow_tray():
        overlay.root.after(500, follow_tray)  # replanifie d'abord : une erreur ponctuelle n'arrete pas le suivi
        tray.refresh(icon)

    overlay.root.after(500, follow_tray)  # laisse a l'icone le temps d'etre prete
    if state.settings["reference"] is None:
        webbrowser.open(server.URL)  # premier lancement : guider la calibration
    overlay.root.mainloop()  # jusqu'a l'arret (state.running = False)

    log.info("Arret")
    icon.stop()
    httpd.shutdown()
    detection.join(timeout=5)


if __name__ == "__main__":
    main()
