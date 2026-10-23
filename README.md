# Assistant de posture

Un petit outil pour Windows et Mac qui vous aide à **garder une bonne posture au bureau**, toute la journée, sans vous déranger.

Il observe votre posture grâce à la webcam et, quand vous vous avachissez ou avancez la tête trop longtemps, il vous le signale **discrètement** : pas de son, pas de fenêtre qui s'ouvre, rien qui interrompe ce que vous tapez.

![Windows 10 et 11](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6) ![macOS Apple Silicon](https://img.shields.io/badge/macOS-Apple%20Silicon-555555) ![Données 100 % locales](https://img.shields.io/badge/donn%C3%A9es-100%20%25%20locales-1f9d55)

---

## Télécharger

| Système | Téléchargement |
|---------|----------------|
| **Windows** 10 ou 11 | 👉 **[AssistantPosture.exe](https://github.com/khaldisamir-ynov/assistant-postural/releases/latest/download/AssistantPosture.exe)** |
| **Mac** à puce Apple (M1 et suivants), macOS 11 ou plus | 👉 **[AssistantPosture-macOS.zip](https://github.com/khaldisamir-ynov/assistant-postural/releases/latest/download/AssistantPosture-macOS.zip)** |

Aucune installation : sous Windows c'est un seul fichier à lancer ; sur Mac, décompressez le zip et glissez **AssistantPosture** dans le dossier **Applications**.

**Il vous faut** une webcam face à vous (celle de l'ordinateur portable suffit).

> Mac à processeur Intel : pas d'application prête pour l'instant, voir « Pour les développeurs » pour la lancer depuis les sources.

---

## Démarrer en 3 étapes

### 1. Lancer l'application

**Windows** : double-cliquez sur `AssistantPosture.exe`.

> **« Windows a protégé votre ordinateur » ?**
> C'est normal pour un logiciel récent et non signé. Cliquez sur **Informations complémentaires**, puis **Exécuter quand même**. Cet avertissement n'apparaît qu'une fois.

**Mac** : ouvrez **AssistantPosture** depuis le dossier Applications.

> **« Apple n'a pas pu vérifier… » ou « AssistantPosture ne peut pas être ouvert » ?**
> C'est normal pour une application non distribuée par l'App Store. Ouvrez **Réglages Système → Confidentialité et sécurité**, descendez jusqu'au message concernant AssistantPosture et cliquez sur **Ouvrir quand même**. Cet avertissement n'apparaît qu'une fois.
>
> Ensuite, macOS demande l'**accès à la caméra** : cliquez sur **Autoriser**.

Le premier démarrage prend quelques secondes. Une page s'ouvre dans votre navigateur.

### 2. Calibrer votre bonne posture

1. Asseyez-vous **bien droit**, face à l'écran, comme vous voudriez vous tenir.
2. Vérifiez dans l'aperçu que votre **tête et vos épaules** sont visibles.
3. Cliquez sur **Calibrer ma posture** et restez immobile 3 secondes.

C'est tout : l'application connaît maintenant votre posture de référence.

### 3. Travailler normalement

Vous pouvez **fermer la page** : l'assistant continue de veiller en arrière-plan. Une icône apparaît :

- **Windows** : près de l'horloge (si vous ne la voyez pas, cliquez sur la petite flèche **^** de la barre des tâches) ;
- **Mac** : dans la barre des menus, en haut à droite.

---

## Comment l'assistant vous prévient

| Situation | Ce que vous voyez |
|-----------|-------------------|
| Posture correcte | Rien. L'icône de l'assistant est **verte**. |
| Mauvaise posture depuis 2 s | Un **fin liseré ambre** pulse doucement en haut de l'écran. |
| Toujours mal installé 30 s plus tard | Une petite **pastille « Redressez-vous »** apparaît dans un coin et indique pourquoi (épaules affaissées, tête en avant). |
| Vous vous redressez | Tout disparaît en douceur. |

Le liseré et la pastille ne bloquent jamais la souris : vous pouvez cliquer à travers. Sur Mac, ils restent visibles sur tous les bureaux et par-dessus les apps en plein écran.

---

## Réglages

Ouvrez les réglages depuis **l'icône de l'assistant** (ou à l'adresse http://127.0.0.1:8765).

- **Tolérance épaules / tête** : plus la valeur est basse, plus l'assistant est exigeant. Les jauges en direct montrent votre écart actuel et le seuil, pour régler en voyant l'effet.
- **Halo après** : combien de secondes de mauvaise posture avant le liseré.
- **Rappel « Redressez-vous »** : l'activer ou non, et après combien de temps.
- **Position** : le coin de l'écran où apparaît la pastille (le liseré suit le bord haut ou bas).
- **Tester le signalement** : pour voir à quoi ressemble l'alerte, sans avoir à se tenir mal.
- **Lancer à l'ouverture de session** : l'assistant démarre tout seul quand vous allumez votre ordinateur.

Changé de chaise, d'écran ou de place ? Cliquez sur **Recalibrer**.

### Menu de l'icône (clic droit sous Windows, clic sur Mac)

- **Ouvrir les réglages**
- **Pause** : à utiliser pendant une **visio**, la webcam est libérée pour Teams, Zoom, etc. Recliquez pour reprendre.
- **Lancer à l'ouverture de session**
- **Quitter**

---

## Vie privée

- **Tout reste sur votre ordinateur.** Aucune image n'est enregistrée ni envoyée sur Internet.
- L'application analyse la position de vos oreilles et de vos épaules, image par image, puis oublie l'image.
- Les réglages de l'interface ne sont accessibles que depuis votre propre ordinateur.
- Seuls vos réglages et votre calibration (quelques nombres) sont conservés, dans `%APPDATA%\AssistantPosture\` (Windows) ou `~/Library/Application Support/AssistantPosture/` (Mac).

---

## Problèmes fréquents

**« Webcam indisponible »**
Une autre application (visio, appareil photo) utilise peut-être la webcam. Fermez-la : l'assistant réessaie tout seul. Vérifiez aussi que l'accès à la caméra est autorisé :
- Windows : *Paramètres → Confidentialité et sécurité → Caméra → Autoriser les applications de bureau à accéder à la caméra* ;
- Mac : *Réglages Système → Confidentialité et sécurité → Caméra* → activez **AssistantPosture**, puis relancez l'application.

**« Hors champ »**
Votre tête ou vos épaules ne sont pas visibles. Reculez un peu ou inclinez l'écran.

**Trop d'alertes**
Augmentez la tolérance ou le délai du halo dans les réglages. Recalibrez si vous avez changé d'installation.

**Pas assez d'alertes**
Diminuez la tolérance, puis vérifiez avec les jauges qu'elles passent bien à l'ambre quand vous vous tenez mal.

**Le lancement ne fait rien de visible**
L'assistant tourne peut-être déjà : les réglages s'ouvrent alors dans votre navigateur. Sinon, attendez quelques secondes, le premier démarrage est un peu long.

**Quelque chose ne marche pas**
Le journal `posture.log` (dans le dossier de réglages indiqué plus haut) contient les détails. Joignez-le à votre signalement dans les [Issues](https://github.com/khaldisamir-ynov/assistant-postural/issues).

---

## Désinstaller

1. Menu de l'icône → décochez **Lancer à l'ouverture de session**, puis **Quitter**.
2. Supprimez `AssistantPosture.exe` (Windows) ou mettez **AssistantPosture** à la corbeille depuis Applications (Mac).
3. (Facultatif) Supprimez le dossier de réglages : `%APPDATA%\AssistantPosture` ou `~/Library/Application Support/AssistantPosture`.

---

## Pour les développeurs

Python 3.9 à 3.12 (MediaPipe 0.10.21), Windows ou macOS.

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.lock -e ".[dev]"   # versions figées
.\.venv\Scripts\python -m posture                              # lancer
.\.venv\Scripts\python -m pytest                               # tests
.\build.ps1                                                    # tests + dist\AssistantPosture.exe
```

Sur Mac : mêmes commandes avec `.venv/bin/` au lieu de `.\.venv\Scripts\`. L'app Mac (`AssistantPosture-macOS.zip`) est construite par GitHub Actions ([`.github/workflows/macos.yml`](.github/workflows/macos.yml)) et ajoutée automatiquement à chaque release `v*`.

| Module | Rôle |
|--------|------|
| `posture/core.py` | Logique de posture pure (mesures, écarts, seuils) |
| `posture/detector.py` | Boucle webcam + MediaPipe, calibration, machine à états |
| `posture/state.py` | État partagé entre fils, réglages validés et persistés |
| `posture/server.py` | Serveur local (`127.0.0.1` uniquement) : interface, aperçu, API JSON |
| `posture/overlay.py` | Liseré et pastille (tkinter + Win32 ou AppKit) |
| `posture/tray.py` | Icône de la zone de notification ou de la barre des menus (pystray) |
| `posture/autostart.py` | Lancement à l'ouverture de session (registre Windows ou LaunchAgent macOS) |
| `posture/index.html` | Interface de configuration |
| `posture_assistant.py` | Version script d'origine (fenêtre OpenCV) |

**Principe** : avec une webcam de face, l'avachissement se voit à la descente des épaules et la tête en avant au rapprochement oreilles-épaules. Les mesures sont divisées par la largeur des épaules pour ne pas dépendre de la distance à la caméra.

**Sécurité** : le serveur n'écoute qu'en local, refuse les en-têtes `Host` étrangers (DNS rebinding) et n'accepte que des `POST` JSON validés : un site web ne peut ni lire la webcam ni piloter l'application.

Historique du projet : [SUIVI_DEVELOPPEMENT.md](SUIVI_DEVELOPPEMENT.md).
