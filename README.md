# Assistant de posture

Application Windows qui surveille votre posture par la webcam, en arrière-plan, et vous le signale **sans son ni fenêtre** :

1. un **halo** ambre fin pulse lentement en bord d'écran quand la mauvaise posture dure (2 s par défaut) ;
2. si elle persiste (30 s), une **pastille « Redressez-vous »** indique le motif (épaules affaissées, tête en avant).

Rien ne prend le focus ni ne bloque les clics. Une icône près de l'horloge indique l'état (vert, ambre, gris en pause) et donne accès aux réglages.

## Utilisation

- Lancer `AssistantPosture.exe` (ou `python -m posture` en développement).
- Au premier lancement, l'interface s'ouvre : asseyez-vous droit et cliquez sur **Calibrer ma posture**.
- Réglages : clic sur l'icône près de l'horloge, ou http://127.0.0.1:8765 (tolérances, délais, position, pause, lancement au démarrage de Windows).
- Pendant une visio : **Pause** (menu de l'icône) libère la webcam.

Réglages, calibration et journal : `%APPDATA%\AssistantPosture\` (`settings.json`, `posture.log`).

## Développement

Python 3.9 à 3.12 (mediapipe 0.10.21).

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.lock -e ".[dev]"   # versions figees
.\.venv\Scripts\python -m posture                              # lancer
.\.venv\Scripts\python -m pytest                               # tests
.\build.ps1                                                    # tests + dist\AssistantPosture.exe
```

| Module | Rôle |
|--------|------|
| `posture/core.py` | Logique de posture pure (mesures, écarts, seuils) |
| `posture/detector.py` | Boucle webcam + MediaPipe, calibration, machine à états |
| `posture/state.py` | État partagé entre fils, réglages validés et persistés |
| `posture/server.py` | Serveur local (`127.0.0.1` uniquement) : interface, aperçu, API JSON |
| `posture/overlay.py` | Halo et pastille (tkinter + styles Win32) |
| `posture/tray.py` | Icône de la zone de notification (pystray) |
| `posture/autostart.py` | Lancement à l'ouverture de session (registre utilisateur) |
| `posture/index.html` | Interface de configuration |
| `posture_assistant.py` | Version script d'origine (fenêtre OpenCV) |

Sécurité : le serveur n'écoute qu'en local, refuse les en-têtes `Host` étrangers (DNS rebinding) et n'accepte que des `POST` JSON validés : un site web ne peut ni lire la webcam ni piloter l'application.
