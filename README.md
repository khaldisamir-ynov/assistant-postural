# Assistant de posture

Un petit outil Windows qui vous aide à **garder une bonne posture au bureau**, toute la journée, sans vous déranger.

Il observe votre posture grâce à la webcam et, quand vous vous avachissez ou avancez la tête trop longtemps, il vous le signale **discrètement** : pas de son, pas de fenêtre qui s'ouvre, rien qui interrompe ce que vous tapez.

![Windows 10 et 11](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6) ![Données 100 % locales](https://img.shields.io/badge/donn%C3%A9es-100%20%25%20locales-1f9d55)

---

## Télécharger

👉 **[Télécharger AssistantPosture.exe](https://github.com/khaldisamir-ynov/assistant-postural/releases/latest/download/AssistantPosture.exe)** (dernière version, environ 135 Mo)

Aucune installation : c'est un seul fichier à lancer.

**Il vous faut** : Windows 10 ou 11 et une webcam face à vous (celle de l'ordinateur portable suffit).

---

## Démarrer en 3 étapes

### 1. Lancer l'application

Double-cliquez sur `AssistantPosture.exe`.

> **Windows affiche « Windows a protégé votre ordinateur » ?**
> C'est normal pour un logiciel récent et non signé. Cliquez sur **Informations complémentaires**, puis **Exécuter quand même**. Cet avertissement n'apparaît qu'une fois.

Le premier démarrage prend quelques secondes. Une page s'ouvre dans votre navigateur.

### 2. Calibrer votre bonne posture

1. Asseyez-vous **bien droit**, face à l'écran, comme vous voudriez vous tenir.
2. Vérifiez dans l'aperçu que votre **tête et vos épaules** sont visibles.
3. Cliquez sur **Calibrer ma posture** et restez immobile 3 secondes.

C'est tout : l'application connaît maintenant votre posture de référence.

### 3. Travailler normalement

Vous pouvez **fermer la page** : l'assistant continue de veiller en arrière-plan. Une icône apparaît près de l'horloge (si vous ne la voyez pas, cliquez sur la petite flèche **^** de la barre des tâches).

---

## Comment l'assistant vous prévient

| Situation | Ce que vous voyez |
|-----------|-------------------|
| Posture correcte | Rien. L'icône près de l'horloge est **verte**. |
| Mauvaise posture depuis 2 s | Un **fin liseré ambre** pulse doucement en haut de l'écran. |
| Toujours mal installé 30 s plus tard | Une petite **pastille « Redressez-vous »** apparaît dans un coin et indique pourquoi (épaules affaissées, tête en avant). |
| Vous vous redressez | Tout disparaît en douceur. |

Le liseré et la pastille ne bloquent jamais la souris : vous pouvez cliquer à travers.

---

## Réglages

Ouvrez les réglages en **cliquant sur l'icône** près de l'horloge (ou à l'adresse http://127.0.0.1:8765).

- **Tolérance épaules / tête** : plus la valeur est basse, plus l'assistant est exigeant. Les jauges en direct montrent votre écart actuel et le seuil, pour régler en voyant l'effet.
- **Halo après** : combien de secondes de mauvaise posture avant le liseré.
- **Rappel « Redressez-vous »** : l'activer ou non, et après combien de temps.
- **Position** : le coin de l'écran où apparaît la pastille (le liseré suit le bord haut ou bas).
- **Tester le signalement** : pour voir à quoi ressemble l'alerte, sans avoir à se tenir mal.
- **Lancer au démarrage de Windows** : l'assistant démarre tout seul à chaque ouverture de session.

Changé de chaise, d'écran ou de place ? Cliquez sur **Recalibrer**.

### Menu de l'icône (clic droit)

- **Ouvrir les réglages**
- **Pause** : à utiliser pendant une **visio**, la webcam est libérée pour Teams, Zoom, etc. Recliquez pour reprendre.
- **Lancer au démarrage de Windows**
- **Quitter**

---

## Vie privée

- **Tout reste sur votre ordinateur.** Aucune image n'est enregistrée ni envoyée sur Internet.
- L'application analyse la position de vos oreilles et de vos épaules, image par image, puis oublie l'image.
- Les réglages de l'interface ne sont accessibles que depuis votre propre ordinateur.
- Seuls vos réglages et votre calibration (quelques nombres) sont conservés, dans `%APPDATA%\AssistantPosture\`.

---

## Problèmes fréquents

**« Webcam indisponible »**
Une autre application (visio, appareil photo) utilise peut-être la webcam. Fermez-la : l'assistant réessaie tout seul. Vérifiez aussi que l'accès à la caméra est autorisé : *Paramètres Windows → Confidentialité et sécurité → Caméra → Autoriser les applications de bureau à accéder à la caméra*.

**« Hors champ »**
Votre tête ou vos épaules ne sont pas visibles. Reculez un peu ou inclinez l'écran.

**Trop d'alertes**
Augmentez la tolérance ou le délai du halo dans les réglages. Recalibrez si vous avez changé d'installation.

**Pas assez d'alertes**
Diminuez la tolérance, puis vérifiez avec les jauges qu'elles passent bien à l'ambre quand vous vous tenez mal.

**Le double-clic sur l'exe ne fait rien de visible**
L'assistant tourne peut-être déjà : les réglages s'ouvrent alors dans votre navigateur. Sinon, attendez quelques secondes, le premier démarrage est un peu long.

**Quelque chose ne marche pas**
Le journal `%APPDATA%\AssistantPosture\posture.log` contient les détails. Joignez-le à votre signalement dans les [Issues](https://github.com/khaldisamir-ynov/assistant-postural/issues).

---

## Désinstaller

1. Clic droit sur l'icône → décochez **Lancer au démarrage de Windows**, puis **Quitter**.
2. Supprimez `AssistantPosture.exe`.
3. (Facultatif) Supprimez le dossier `%APPDATA%\AssistantPosture` (réglages et journal).

---

## Pour les développeurs

Python 3.9 à 3.12 (MediaPipe 0.10.21), Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.lock -e ".[dev]"   # versions figées
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
| `posture/overlay.py` | Liseré et pastille (tkinter + styles Win32) |
| `posture/tray.py` | Icône de la zone de notification (pystray) |
| `posture/autostart.py` | Lancement à l'ouverture de session (registre utilisateur) |
| `posture/index.html` | Interface de configuration |
| `posture_assistant.py` | Version script d'origine (fenêtre OpenCV) |

**Principe** : avec une webcam de face, l'avachissement se voit à la descente des épaules et la tête en avant au rapprochement oreilles-épaules. Les mesures sont divisées par la largeur des épaules pour ne pas dépendre de la distance à la caméra.

**Sécurité** : le serveur n'écoute qu'en local, refuse les en-têtes `Host` étrangers (DNS rebinding) et n'accepte que des `POST` JSON validés : un site web ne peut ni lire la webcam ni piloter l'application.

Historique du projet : [SUIVI_DEVELOPPEMENT.md](SUIVI_DEVELOPPEMENT.md).
