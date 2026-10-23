# Suivi de développement — Assistant de posture

**Objectif** : application locale qui aide à garder une bonne posture toute la journée au bureau, avec une alerte silencieuse et non intrusive.

**Version actuelle** : 0.3.0 (Windows + macOS). Architecture et commandes dans le [README](README.md).

## Avancement

| Étape | Description | Statut |
|-------|-------------|--------|
| 1 | Initialisation et flux vidéo (webcam, effet miroir, boucle d'affichage) | ✅ Fait |
| 2 | Intégration MediaPipe Pose (BGR → RGB, dessin du squelette) | ✅ Fait |
| 3 | Calibration (compte à rebours 3 s, moyenne des mesures) | ✅ Fait |
| 4 | Calcul de posture (avachissement + tête en avant) | ✅ Fait |
| 5 | Gestion du temps et alertes | ✅ Fait |
| 6 | Réglage des seuils sur personne réelle | ✅ Fait (tolérances 3 % / 5 %, délai 2 s) |
| 7 | POC application locale : interface web + alerte silencieuse | ✅ Validé |
| 8 | MVP : paquet Python, tests, arrière-plan (icône), signalement en escalade, exe, démarrage auto | ✅ Fait, publié (v0.2.0) |
| 9 | Support macOS (Apple Silicon) : app construite par GitHub Actions | 🧪 Construit en CI, à tester sur un vrai Mac |

## 0.3.0 : support macOS

- **Indicateur** : mêmes halo et pastille ; sous macOS, transparence native de Tk et fenêtres AppKit (PyObjC) réglées pour laisser passer les clics et rester visibles sur tous les bureaux et au-dessus des apps en plein écran.
- **Icône de la barre des menus** : pystray partage l'application Cocoa de Tk ; toutes les mises à jour de l'icône passent par la boucle Tk (fil principal, exigé par AppKit). Même code sous Windows.
- **Caméra** : l'autorisation est demandée depuis le fil principal au démarrage (contrainte d'OpenCV/AVFoundation) ; `NSCameraUsageDescription` ajoutée à l'app.
- **Ouverture de session** : LaunchAgent `~/Library/LaunchAgents/com.assistantposture.plist`.
- **Réglages et journal** : `~/Library/Application Support/AssistantPosture/`.
- **Distribution** : `.github/workflows/macos.yml` construit `AssistantPosture-macOS.zip` (tests, PyInstaller, `LSUIElement` pour une app sans icône de Dock, signature ad hoc) et l'ajoute à chaque release `v*`.
- **Limites** : Apple Silicon uniquement (pas d'app Intel) ; app non signée par un compte Apple Developer, donc « Ouvrir quand même » au premier lancement ; non testée sur un vrai Mac à ce stade.

## MVP 0.2.0

### Mode arrière-plan
- **Icône de la zone de notification** (pystray) : couleur selon l'état (vert OK, ambre alerte ou calibration nécessaire, gris pause ou hors champ, rouge webcam/erreur). Menu : Ouvrir les réglages, Pause, Lancer au démarrage de Windows, Quitter.
- **Sans console** : `pythonw` ou exe `--windowed` ; tout est journalisé dans `%APPDATA%\AssistantPosture\posture.log` (tournant, 3 × 1 Mo).
- **Démarrage automatique** : clé `HKCU\...\Run` (sans droits admin). Au démarrage, le navigateur ne s'ouvre que si aucune calibration n'existe.
- **Instance unique** : un 2e lancement ouvre simplement l'interface de l'instance active (`allow_reuse_address = False`, sinon Windows laisse deux serveurs écouter le même port).
- **Robustesse** : la détection redémarre seule après une erreur inattendue ; webcam prise → nouvel essai toutes les 2 s.

### Signalement en escalade douce
1. Après le délai d'alerte : **halo** ambre de 5 px sur le bord haut (ou bas) de l'écran, pulsation lente.
2. Après le délai de rappel (30 s par défaut) : **pastille** « Redressez-vous » + motif, dans le coin choisi.
- Fenêtres Win32 `TRANSPARENT | NOACTIVATE | TOOLWINDOW | LAYERED` : clics traversants, jamais de focus, hors Alt+Tab (vérifié : exstyle `0x080800A8`).
- Apparition / disparition en fondu ; compatible écrans mis à l'échelle (DPI aware, vérifié en 2880×1920 à 200 %).

### Interface de configuration
- **Jauges en direct** de l'écart aux références (épaules, tête) avec le seuil matérialisé : on règle les tolérances en voyant l'effet.
- **Tester le signalement** : affiche halo + pastille 6 s sans avoir à se tenir mal.
- Réglages groupés (Détection, Signalement, Système) ; mini-écran pour choisir le coin ; bornes des tolérances abaissées à 1 %.
- **Aperçu webcam repliable** : quand il est replié, aucune image n'est encodée (économie CPU sur la journée).

### Industrialisation
- Paquet `posture/` (`pyproject.toml`, version unique dans `posture/__init__.py`), dépendances figées dans `requirements.lock`.
- 28 tests pytest : logique de posture, validation et chargement tolérant des réglages, machine à états (calibration, délai d'alerte), serveur (Host étranger, POST non JSON, bornes, instance unique).
- `build.ps1` : tests puis `dist\AssistantPosture.exe` (PyInstaller, un seul fichier, sans console).
- Réglages déplacés dans `%APPDATA%\AssistantPosture\` (l'exe peut être placé dans un dossier non inscriptible). Calibration du POC reprise.
- POC retiré (`app.py`, `index.html` racine) : remplacé par le paquet.

## Choix techniques

- **MediaPipe épinglé à `0.10.21`** : les versions récentes ont retiré `mp.solutions`. Python 3.9 à 3.12.
- **Repères utilisés** : oreilles (7, 8) et épaules (11, 12). Le nez (0) n'est pas utilisé : il bouge dès qu'on regarde le clavier.
- **Mesures normalisées par la largeur des épaules** : indépendantes de la distance à la caméra ; identiques avec ou sans effet miroir.
- **Tête en avant (vue de face)** : baisse relative de la distance verticale oreilles → épaules. La distance horizontale n'est visible que de profil.
- **Avachissement** : descente des épaules, en fraction de largeur d'épaules.
- **Hors champ** : visibilité < 0.5 sur oreilles ou épaules → analyse suspendue sans alerte.
- **10 images/s** : suffisant pour la posture, ménage le CPU toute la journée.
- **Serveur HTTP de la bibliothèque standard** : aucun framework nécessaire pour 5 routes locales.
- **Sécurité** : `127.0.0.1` uniquement ; contrôle de l'en-tête `Host` (anti DNS rebinding) ; `POST` en JSON obligatoire (preflight CORS) ; validation et bornes de chaque réglage.

## Réglages par défaut

| Réglage | Valeur | Rôle |
|---------|--------|------|
| `slouch_threshold` | 0.03 | Tolérance épaules (1 % à 40 %) |
| `head_threshold` | 0.05 | Tolérance tête (1 % à 50 %) |
| `alert_delay` | 2 s | Mauvaise posture tolérée avant le halo |
| `escalation_delay` | 30 s | Halo → pastille |
| `show_pill` | oui | Afficher la pastille de rappel |
| `overlay_corner` | haut droite | Coin de la pastille (le halo suit le bord) |

## Journal

### 2026-10-23
- Script `posture_assistant.py` (étapes 1 à 5), environnement `.venv`, premier lancement webcam réussi.
- POC application locale (serveur web + point ambre), vérifications de sécurité.
- Réglages validés en usage réel : épaules 3 %, tête 5 %, délai 2 s, coin haut droite → valeurs par défaut.
- MVP 0.2.0 : paquet, tests, icône, halo + pastille, interface repensée, exe, démarrage auto. Publié sur GitHub (release v0.2.0).
- 0.3.0 : support macOS ; Windows revérifié (tests, signalement, arrêt propre).

## Prochaines étapes

- [ ] Tester l'app macOS sur un vrai Mac : lancement, autorisation caméra, icône de barre des menus, halo et pastille.
- [ ] Utiliser le MVP une journée complète : gêne du halo et de la pastille, fréquence des alertes, CPU.
- [ ] Icône dédiée pour l'exe (actuellement l'icône PyInstaller par défaut).
- [ ] Limites connues : écran principal seulement, position recalculée seulement au changement de coin (barre des tâches déplacée en cours de route non prise en compte).
- [ ] Pistes : statistiques de la journée (temps en bonne posture), CI (tests + build de l'exe à chaque push), signature de l'exe (évite l'avertissement SmartScreen).
