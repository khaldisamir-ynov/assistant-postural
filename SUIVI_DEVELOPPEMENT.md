# Suivi de développement — Assistant de posture

**Objectif** : application locale qui aide à garder une bonne posture toute la journée au bureau, avec une alerte silencieuse et non intrusive.

**Version actuelle** : 0.4.0 (Windows + macOS). Architecture et commandes dans le [README](README.md).

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
| 10 | Modèle Hugging Face : essai profondeur (no-go), statistiques du jour, coach LLM, lissage, lieux, écrans multiples | ✅ Fait (0.4.0, non publié) |

## 0.4.0 : statistiques, coach IA Hugging Face, lissage, lieux et écrans multiples

### Précision : essai du 2026-10-30
Enregistrement de 10 postures × 12 s (~360 images chacune), uniquement les 33 repères MediaPipe et des silhouettes, puis **rejeu dans la vraie logique de détection** (banc d'essai).
- **Penché / accoudé** : pente de la ligne des épaules, 0,165 contre 0,055 au plus dans les autres postures → seuil `0.10`. Détecté à 100 %.
- **Trop près de l'écran** : épaules +73 % plus larges contre +10 % au plus → seuil `0.25`. Détecté à 100 %. Les motifs épaules et tête sont alors masqués, car la perspective les fausse.
- **Tête en avant ou clavier** : dans cet essai, regarder le clavier ne fait pas dépasser le seuil de la tête (+2 %). Le nez n'apporte rien de plus, donc il n'est pas ajouté.
- **Calibration**, principale source d'erreur :
  - les 3 premières secondes sont 20 à 50 fois plus bruitées (on se replace) ;
  - les épaules étaient à 80 % de la hauteur de l'image, en bord bas où MediaPipe est instable.

  Corrections : première seconde ignorée, médiane, calibration refusée si l'on bouge (écart-type supérieur à 3 % de la largeur des épaules), avertissement si les épaules sont sous 75 % de l'image.
- **Tolérance épaules par défaut : 3 % → 5 %.** Assis droit, les épaules descendent naturellement d'environ 5 % en quelques secondes. À 3 %, la posture droite est signalée environ la moitié du temps ; à 5 %, environ 20 %. Les postures fautives restent toutes détectées.
- **VLM sur silhouette : no-go.** Qwen3.8-27B (routeur HF) sur 30 silhouettes : environ 7 réponses justes, au niveau du hasard ; le téléphone n'est jamais reconnu. Le cadrage webcam ne montre presque pas les mains. Non intégré.
- **Tête appuyée sur la main** : distance entre la main (poignets et doigts MediaPipe 15 à 20) et le nez, mesurée en écarts d'yeux. Menton dans la main : 1,4 contre 2,4 ou plus ailleurs → seuil `2.0`. Détection de cette posture : 24-33 % → 97 %.
- **Outils d'essai** dans `essais/` : `enregistrer.py` (essai guidé, repères uniquement) et `rejouer.py` (banc qui rejoue un essai dans la vraie logique et vérifie les critères). Données dans `essais/donnees/`, exclues de git.
- **SPECIFICATIONS.md** : exigences, critères de réussite, protocole d'essai, résultats (11 critères sur 16) et scénario de démo. Référence avant toute nouvelle modification.
- Performance mesurée : 1,3 % du processeur de la machine, 307 Mo de mémoire.
- **Limite restante** : téléphone et boisson déclenchent « tête en avant ». La géométrie ne peut pas les distinguer (mains hors champ) ; seul un VLM sur la photo le pourrait, ce qui demanderait d'envoyer l'image (refusé pour l'instant).

- **Lieux de travail** (Bureau, Maison…, noms libres, 10 au plus), choisis à la main dans la page ou le menu de l'icône.
  - Chaque lieu garde ses calibrations ; tolérances et délais restent communs.
  - Ancienne calibration reprise dans « Mon poste ».
- **Plusieurs écrans** : « Ajouter un écran » enregistre une référence de plus pour le lieu (4 au plus). La posture est jugée par rapport à la référence la plus proche, en écart absolu.
  - Premier choix écarté par un test : retenir la référence « la plus favorable » rendait le choix ambigu, car se tourner fait baisser l'écart de la tête.
  - Limite : la proximité ne repose que sur les écarts épaules et tête. Ajouter l'orientation si deux écrans se confondent.

- **Lissage** : les mesures sont moyennées sur ~1 s (10 images) avant d'être comparées aux seuils.
- **Hystérésis** : une fois en mauvaise posture, retour à « OK » seulement sous 80 % du seuil. L'état ne clignote plus autour du seuil.
- **Statistiques du jour** (`posture/stats.py`) : secondes en bonne et en mauvaise posture, par motif, et nombre d'alertes.
  - Enregistrées dans `stats.json` (dossier de réglages) toutes les 60 s et à l'arrêt, remises à zéro chaque jour.
  - Les pauses et les coupures de webcam ne comptent pas.
- **Coach IA** (`posture/coach.py`) : `POST /api/coach` → routeur Hugging Face (`Qwen/Qwen3.8-27B:cerebras`), qui renvoie 3 conseils.
  - Seuls des chiffres agrégés sont envoyés.
  - Token de l'utilisateur, validé (`hf_…`) et jamais renvoyé à la page. En-tête `X-HF-Bill-To` facultatif.
  - Aucune nouvelle dépendance : `urllib` de la bibliothèque standard.
  - Piège : sans `User-Agent` explicite, le pare-feu de Hugging Face renvoie 403 à `urllib`.
- Réponse du LLM affichée en `textContent`, jamais interprétée comme du HTML.
- `mon_script.py` : test autonome du LLM avec le `.env`, hors application.
- Tests : 42 OK (statistiques, coach simulé, hystérésis, token jamais renvoyé, lieux, écrans multiples).

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
| `slouch_threshold` | 0.05 | Tolérance épaules (1 % à 40 %) |
| `head_threshold` | 0.05 | Tolérance tête (1 % à 50 %) |
| `lean_threshold` | 0.10 | Tolérance inclinaison des épaules (3 % à 50 %) |
| `close_threshold` | 0.25 | Tolérance distance à l'écran : élargissement des épaules (5 % à 100 %) |
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

### 2026-10-30 : essai d'un modèle Hugging Face (Depth Anything V2 Small)
- Idée : mesurer la profondeur tête / épaules pour mieux détecter la tête en avant. Modèle `onnx-community/depth-anything-v2-small`, int8, onnxruntime, en local.
- Essai webcam, 5 postures de 15 s. Écart à la posture droite, en écarts-types :

  | Mesure | Tête en avant | Regard clavier | Avachi |
  |--------|---------------|----------------|--------|
  | Ratio 2D actuel (`head_ratio`) | +9,0 σ (+6,4 %) | +10,6 σ (+7,5 %) | +5,1 σ |
  | MediaPipe `z` (gratuit) | −4,3 σ | −5,5 σ | −2,1 σ |
  | Depth Anything | +3,3 σ (+4,4 %) | +4,3 σ (+5,7 %) | +1,0 σ |

- **Décision : no-go.** La profondeur ne fait pas mieux que la mesure 2D actuelle et ne distingue pas plus qu'elle la tête en avant du regard vers le clavier. Elle coûte cher : 2,3 s par image sur 1 cœur, 0,6 s sur 4.
- Limite : 7 mesures par posture seulement, à cause de cette lenteur, et la mesure droite dérive entre le début et la fin (« droit2 »).
- Test du LLM Hugging Face (routeur HF, Qwen 3.8, facturé à `ynov`) : `mon_script.py` envoie des statistiques de posture, uniquement des chiffres, et reçoit 3 conseils en 1,4 s. Le token est dans `.env`, exclu de git.

### 2026-10-30 : webcam déplacée (F13), essai n° 1
- Constat : déplacer ou incliner l'ordinateur fausse la calibration. Recalibrer à chaque fois est inacceptable pour l'utilisateur.
- VLM écarté pour ce problème : il est géométrique, et un VLM ne mesure pas des écarts de quelques %.
- Méthode testée : on mesure le décalage du **décor**, avec des points ORB pris hors de la silhouette grâce à la segmentation MediaPipe, puis on l'applique à la référence. Vérifiée sur une image de synthèse : échelle, rotation et décalage retrouvés exactement.
- Essai n° 1 (`essais/enregistrer_camera.py`, `essais/analyser_camera.py`) :
  - la compensation ramène l'erreur de 29 % à 6 % (écran incliné vers l'arrière) et de 55 % à 3 % (vers l'avant) ;
  - critères C8 non atteints, mais le protocole mélange compensation et changement de posture (on se rassoit autrement).
  - Détail et protocole n° 2 dans SPECIFICATIONS.md § 6.4.

### 2026-10-30 : démarche étape par étape (une détection, un paramètre)
- Plusieurs détections ajoutées d'un coup rendaient les erreurs impossibles à attribuer. Désormais : un paramètre par étape, critères fixés avant l'essai, seuil réglé sur les essais enregistrés (`essais/rejouer.py --etape N`), puis essai de validation.
- Documents pour le formateur : `specifications-assistant-postural.docx` (exigences, critères d'acceptation CA1 à CA20, protocole d'essai) et `Specifications_Assistant_Posture.docx` (version complète).

**Étape 1, posture affaissée.** Paramètre : hauteur du haut de la tête (estimé à 1,5 écart d'yeux au-dessus des yeux) jusqu'aux épaules, divisée par la largeur des épaules. C'est un rapport interne au corps, donc insensible à un déplacement de l'ordinateur.
- Seuil : 3 % de raccourcissement.
- Rejeu : tête en avant 100 %, avachi 98 %, aucune alerte en posture droite ni au clavier ; ordinateur déplacé : aucune alerte.
- Reste en échec : 15 % des images signalées en regardant le clavier (limite 10 %), sans alerte.
- **Essai de validation à faire** : la première tentative s'est arrêtée faute d'appui sur ESPACE ; reportée à la demande de l'utilisateur.
- Les autres détections sont désactivées par défaut. Une nouvelle calibration est nécessaire, car les anciennes n'ont pas ce paramètre.

**Étape 2, penché ou accoudé.** Paramètre : angle de l'axe du cou (milieu des oreilles → milieu des épaules), en degrés. Il remplace la pente des épaules.
- Comparaison sur les essais : penché 12,3° contre 2,3° au plus sinon (marge 5,3 fois ; pente des épaules : 2,9 fois) ; ordinateur déplacé : 2,9° au plus.
- Seuil : 6°. Tout seuil entre 4° et 10° atteint les critères ; 6° garde la marge au-dessus du bruit (0,5°) et des mouvements de l'ordinateur.
- Rejeu : penché 100 %, aucun nouveau faux motif, résultats de l'étape 1 inchangés. **Essai de validation à faire.**

### 2026-11-06 : jeu de données généré (Hugging Face) pour sortir du cas d'une seule personne
- But : mesurer l'effet de chaque modification sur d'autres personnes que l'utilisateur. Une image « droit » est générée (Qwen-Image), puis modifiée pour chaque posture, pour garder la même personne et la même caméra.
- Mesures MediaPipe, écarts à l'image « droit » :
  - **Qwen-Image-Edit** : la photo témoin « droit2 » (rien ne doit changer) affiche un raccourcissement de 16,5 % (seuil 3 %) et des épaules 24 % plus larges, avec des couleurs saturées. La modification déplace le corps plus que les postures à détecter.
  - **FLUX.1-Kontext** : témoin stable (0,4 %, 0,9°) et images réalistes, mais tête en avant inchangée (−1,9 %), avachi faisant *monter* les épaules, penché à 3,9° (seuil 6°). Téléphone à l'oreille réussi.
- Décision : les images générées ne notent **pas** les postures fines. Elles servent aux postures visibles sur une seule image (téléphone, boisson, menton dans la main : essai VLM C9) et à la robustesse de MediaPipe sur des profils variés. Les postures fines se généralisent avec des enregistrements de repères d'autres personnes.
- Outils : `essais/generer_images.py`, `essais/images_vers_reperes.py` (photos → repères pour `rejouer.py`), et `rejouer.py` qui accepte plusieurs essais et donne un total d'échecs à comparer avant et après chaque modification.
- **Tri automatique** (`essais/valider_images.py`, critères C10 fixés avant le tri) : MediaPipe Pose et ObjectDetector, indépendants des VLM notés.
  - EfficientDet-Lite0 prenait les tasses pour des téléphones (5 faux rejets sur 8, vérifiés à l'œil) ; remplacé par Lite2.
  - Bilan : 37 photos valables sur 40 après 2 relances. Rejets justifiés : modification qui déplace le corps (droit2), main loin du menton.
- **VLM (C9, provisoire)** : gemma-4-26B et Qwen3-VL-30B à 16/16 reconnus, 0/21 excusés à tort, 1,2 s et 2,5 s, mêmes réponses en 2e passe. gemma-3-4B écarté (« téléphone » partout).
  - GLM-4.6V rendait des réponses vides (sa réflexion consommait les 20 jetons) : budget porté à 1000.
- Détail au § 6.5 de SPECIFICATIONS.md. À faire : confirmer sur de vraies photos (`enregistrer.py --photos`) avant toute intégration.

## Prochaines étapes

- [ ] Tester l'app macOS sur un vrai Mac : lancement, autorisation caméra, icône de barre des menus, halo et pastille.
- [ ] Utiliser le MVP une journée complète : gêne du halo et de la pastille, fréquence des alertes, CPU.
- [ ] Icône dédiée pour l'exe (actuellement l'icône PyInstaller par défaut).
- [ ] Limites connues : écran principal seulement, position recalculée seulement au changement de coin (barre des tâches déplacée en cours de route non prise en compte).
- [ ] Historique sur plusieurs jours ; bilan du coach proposé automatiquement en fin de journée.
- [ ] Pistes : CI (tests + build de l'exe à chaque push), signature de l'exe (évite l'avertissement SmartScreen).
