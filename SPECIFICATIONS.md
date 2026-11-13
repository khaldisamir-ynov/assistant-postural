# Spécifications, critères de réussite, essais et démo

Assistant de posture, version 1.0.0 (MVP). Document de référence **avant toute nouvelle modification** : chaque amélioration doit dire quel critère elle vise, et se vérifier avec le protocole décrit ici.

Historique et choix techniques : [SUIVI_DEVELOPPEMENT.md](SUIVI_DEVELOPPEMENT.md). Utilisation : [README.md](README.md).

---

## 1. Objet et périmètre

**Problème** : au bureau, on prend de mauvaises postures sans s'en rendre compte, et on les garde des heures.

**Objectif** : une application de bureau locale qui détecte les mauvaises postures par la webcam et les signale **discrètement** (sans son, sans fenêtre, sans voler le focus), pour que l'utilisateur en prenne conscience et se redresse.

**Utilisateur** : une personne seule devant son ordinateur, webcam face à elle, sur Windows 10/11 ou un Mac Apple Silicon. Elle peut travailler dans plusieurs lieux (bureau, maison, café) et avec plusieurs écrans.

**Hors périmètre** :
- diagnostic médical ;
- suivi de plusieurs personnes ;
- vue de profil ;
- analyse des jambes ou des hanches (hors champ d'une webcam d'ordinateur) ;
- ordinateur posé sur les genoux : la webcam suit le buste, donc s'avachir ne change pas l'image (essai du 2026-11-06 : avachi non détecté sur un canapé, contre 98 % sur un bureau le 2026-10-30) ;
- enregistrement d'images.

---

## 2. Exigences fonctionnelles

| ID | Exigence |
|----|----------|
| **F1** | Détecter les mauvaises postures par rapport à la posture de référence de l'utilisateur : **posture affaissée**, **tête en avant**, **penché sur le côté / accoudé**, **trop près de l'écran**, **tête appuyée sur la main**, et en option **buste affaissé** (axe tête → bassin). La détection « épaules affaissées » a été retirée le 2026-11-13 (§ 6.6). |
| F2 | Chaque détection peut être activée ou désactivée, et sa tolérance est réglable. |
| F3 | Un mouvement bref ne déclenche rien : la mauvaise posture doit durer (délai réglable, 2 s par défaut). Les mesures sont lissées sur ~1 s et le retour à « OK » exige de repasser sous 80 % du seuil (hystérésis). |
| **F4** | Signalement en escalade douce : liseré ambre pulsant en bord d'écran, puis après 30 s (réglable) une pastille « Redressez-vous » avec le motif. Les deux laissent passer les clics et ne prennent jamais le focus. |
| **F5** | Calibration de 3 s : la première seconde est ignorée, la référence est la médiane des mesures. Elle est **refusée si l'utilisateur bouge**, avec un message. Si les épaules sont trop bas dans l'image, un avertissement s'affiche. |
| **F6** | **Lieux de travail** nommés librement (10 au plus), choisis à la main dans la page ou dans le menu de l'icône. Chaque lieu garde ses propres calibrations. |
| **F7** | **Plusieurs écrans** : jusqu'à 4 références par lieu (« Ajouter un écran »). La posture est jugée par rapport à la référence la plus proche. |
| F8 | Hors champ (tête ou épaules invisibles) : aucune alerte. Webcam prise par une autre application : nouvel essai toutes les 2 s. **Pause** : la webcam est libérée. |
| F9 | **Statistiques du jour** : temps en bonne posture, temps suivi, nombre d'alertes, motif principal. Remises à zéro chaque jour. |
| F10 | **Coach IA** (facultatif) : un LLM Hugging Face rédige un rapport de journée (bilan, postures à surveiller, moments de la journée, 3 conseils) à partir des statistiques du jour et des 7 derniers jours, avec le token de l'utilisateur. |
| F11 | Interface de configuration locale (http://127.0.0.1:8765) : état, jauges en direct, réglages, test du signalement, aperçu webcam repliable. |
| F12 | Fonctionnement en arrière-plan : icône de notification (Windows) ou de barre des menus (Mac), lancement à l'ouverture de session, une seule instance. |
| **F13** *(prévue)* | **Webcam déplacée sans recalibrage** : quand l'ordinateur est incliné, tourné ou déplacé, l'assistant mesure le décalage du décor et l'applique à la posture de référence. **Aucune action de l'utilisateur.** Si la compensation est impossible (décor méconnaissable, trop peu de repères), les alertes sont suspendues plutôt que fausses. |
| F14 *(prévue)* | **Lieu reconnu automatiquement** par la même empreinte du décor ; le choix manuel reste possible. Une seule calibration par nouveau lieu. |
| F15 *(prévue)* | **Dérive lente** : quand l'utilisateur est dans la tolérance, la référence le suit lentement, avec un écart maximal borné pour ne jamais « apprendre » une mauvaise posture. |

## 3. Exigences non fonctionnelles

| ID | Exigence |
|----|----------|
| **N1 Vie privée** | Aucune image n'est enregistrée ni envoyée. Seul le coach (s'il est activé) envoie des **chiffres agrégés** à Hugging Face. L'empreinte du décor (F13, F14) n'est pas une image : des coordonnées de points et des codes binaires, qui restent sur l'ordinateur. |
| N2 Sécurité | Serveur sur `127.0.0.1` uniquement ; en-tête `Host` contrôlé (anti DNS rebinding) ; `POST` JSON obligatoire ; chaque réglage validé et borné ; le token n'est jamais renvoyé à la page ; la réponse du LLM est affichée comme du texte, jamais comme du HTML. |
| N3 Performance | 10 images/s analysées ; au plus 5 % du processeur de la machine en moyenne et 500 Mo de mémoire. |
| N4 Robustesse | La détection redémarre seule après une erreur. Un fichier de réglages ou de statistiques abîmé n'empêche pas le démarrage et ne fait pas perdre les calibrations valides. |
| N5 Installation | Un seul fichier à lancer (exe Windows, app Mac), sans droits administrateur. |

---

## 4. Critères de réussite

Fixés le 2026-10-30. **On ne les modifie pas après avoir vu des résultats** ; toute modification est datée et justifiée ici.

### 4.1 Détection (vérifiée par le banc d'essai, § 5.2)

| ID | Situation | Critère « alerte » (ce que voit l'utilisateur) | Critère « images » (précision fine) |
|----|-----------|------------------------------------------------|-------------------------------------|
| C1 | Bonne posture : droit (début et fin), regard vers le clavier | **Aucune alerte** pendant 12 s | ≤ 10 % des images signalées |
| C2 | Mauvaise posture : tête en avant, avachi, penché, menton dans la main, trop près | **Au moins une alerte** | Le **bon motif** sur ≥ 90 % des images |

### 4.2 Autres critères

| ID | Critère | Vérification |
|----|---------|--------------|
| C3 | Processeur ≤ 5 % de la machine, mémoire ≤ 500 Mo | Mesure sur 30 s, assistant actif (§ 5.3) |
| C4 | Tous les tests automatiques passent | `pytest` |
| C5 | Hors champ, pause, webcam occupée : aucune alerte, reprise automatique | Essais manuels (§ 5.3) |
| C6 | Se tourner vers un 2e écran calibré ne déclenche pas d'alerte | Essai manuel (§ 5.3) |
| C7 | Aucune image écrite sur disque ni envoyée sur le réseau | Relecture du code et contenu du dossier de réglages |

### 4.3 Webcam déplacée (F13), ajoutés le 2026-10-30 avant l'essai

L'utilisateur reste **droit** et ne recalibre pas. On note *écart résiduel* l'écart de hauteur des épaules par rapport à la référence, une fois la compensation appliquée, en largeurs d'épaules.

| ID | Situation | Critère |
|----|-----------|---------|
| C8a | Écran incliné d'environ 10° vers l'arrière, puis vers l'avant ; ordinateur tourné d'environ 10° | Écart résiduel **≤ 2,5 %** (la moitié de la tolérance épaules) sur ≥ 90 % des images, et **aucune alerte** |
| C8b | Ordinateur déplacé d'environ 10 cm sur le bureau | Même critère que C8a |
| C8c | Changement d'éclairage (lampe, rideau), ordinateur immobile | Aucun déplacement détecté à tort (décalage estimé < 1 % de l'image), aucune alerte |
| C8d | Avachissement **sans toucher l'ordinateur** | La compensation ne l'absorbe pas : décalage estimé < 1 % de l'image, alerte « épaules » déclenchée |
| C8e | Compensation impossible (repères insuffisants) | Signalée, alertes suspendues : jamais de fausse alerte |
| C8f | Délai | Compensation appliquée moins de 10 s après le mouvement |

### 4.4 Téléphone et boisson par VLM (priorité 4), ajoutés le 2026-11-06 avant l'essai

Essai sur **photos** (pas sur silhouette) avec des VLM du routeur Hugging Face. Les photos quittent la machine : essai seulement, avec l'accord des personnes filmées ; C7 reste exigé pour l'application. Photos réelles (`essais/enregistrer.py --photos`) ou générées pour des personnes variées (`essais/generer_images.py`), puis `essais/comparer_vlm.py`. Un résultat obtenu sur images générées doit être confirmé sur quelques photos réelles.

| ID | Critère |
|----|---------|
| C9a | Téléphone ou boisson reconnu (bon mot) sur **≥ 90 %** des photos « telephone » et « boire » |
| C9b | Autres postures, dont tête en avant, excusées à tort (réponse « telephone » ou « boisson ») sur **≤ 5 %** des photos : le VLM ne doit pas masquer une vraie mauvaise posture |
| C9c | Latence médiane **≤ 3 s** (une question par alerte « tête », pas à chaque image) |

### 4.5 Validité du jeu d'images généré (C10), ajoutés le 2026-11-06 avant le tri

Une photo générée n'entre dans le jeu que si elle montre ce que dit son nom. Les contrôles sont **indépendants des VLM notés** : un tri fait par un VLM favoriserait les modèles qui lui ressemblent. Ils utilisent MediaPipe Pose et MediaPipe ObjectDetector (EfficientDet-Lite2, classes COCO, score ≥ 0,3).

*Modification du 2026-11-06 (l'outil, pas les critères)* : le premier tri utilisait EfficientDet-Lite0. Il a rejeté les 5 tasses sur 8 tenues à la bouche, en les prenant pour des téléphones (vérifié à l'œil). Avec Lite2, les 8 tasses obtiennent un score d'au moins 0,44 et les 8 téléphones d'au moins 0,32. Le seuil reste 0,3. Outil : `essais/valider_images.py`, qui déplace les rejets dans `photos_rejetees/` sans rien supprimer et note leur motif dans `rejets.jsonl`.

| ID | Photo | Valide si |
|----|-------|-----------|
| C10a | toutes | Tête et épaules vues par MediaPipe |
| C10b | droit2 (témoin) | Écarts à « droit » sous le tiers des seuils de l'application : raccourcissement < 1 %, cou < 2°, largeur des épaules < 8,3 % |
| C10c | droit, droit2 | Ni téléphone ni boisson détectés ; aucune main près du visage (< 2 écarts d'yeux) |
| C10d | menton_main | Main près du visage ; ni téléphone ni boisson |
| C10e | telephone | Téléphone (`cell phone`) détecté |
| C10f | boire | Boisson (`cup`, `bottle` ou `wine glass`) détectée |

« droit » rejetée : toute la série de la personne est écartée, puisque les autres photos sont faites à partir d'elle.

### 4.6 MediaPipe, VLM ou LLM : comparaison (C11), ajoutés le 2026-11-13 avant l'essai

Question : un modèle de langage, avec ou sans image, détecte-t-il les mauvaises postures mieux que l'approche actuelle ?

**Jeu** : photos réelles prises sur un bureau (`enregistrer.py --photos`). La posture demandée par la consigne donne l'étiquette. La calibration est faite sur les photos « droit ». Outil : `essais/comparer_approches.py`.

**Approches comparées**, toutes sur les mêmes photos et avec la même question :

| | Approche | Ce qui sort du poste |
|---|---|---|
| A | MediaPipe + seuils de l'application (réglages par défaut) | rien |
| B | VLM, photo seule | la photo |
| C | VLM, photo de référence « droit » + photo courante | 2 photos |
| D | LLM texte, repères MediaPipe de référence et courants (des nombres, comme le coach) | des nombres |
| E | A, puis B confirme ou annule chaque alerte de A | 1 photo par alerte |

**Tâches** :
- **Principale (alerte oui ou non)**, sur les détections actives par défaut :
  - alerte attendue : tête en avant, avachi, penché ;
  - aucune alerte attendue : droit, droit2, clavier.
- **Motif**, 5 classes : correcte ; affaissée (tête en avant ou avachi, un seul motif dans l'application) ; penchée ; trop près ; menton dans la main. Pour l'approche A, toutes les détections sont activées. Les photos téléphone et boisson sont rapportées à part, sans être notées.

**Mesures** :
- rappel des mauvaises postures et taux de fausses alertes, chacun avec un intervalle de Wilson à 95 % ;
- exactitude du motif ;
- latence médiane et p95 ;
- coût estimé par heure : une analyse toutes les 5 s pour B, C et D ; un appel par alerte pour E ;
- stabilité sur une 2e passe.

| ID | Critère pour qu'une approche remplace ou complète A |
|----|------------------------------------------------------|
| C11a | Rappel des mauvaises postures **au moins égal** à celui de A |
| C11b | Fausses alertes **≤ 10 %** (comme C1) |
| C11c | Latence médiane **≤ 3 s** |
| C11d | Si des photos sortent du poste : seulement en **option désactivée par défaut**, avec consentement. Elle ne peut pas remplacer A, à cause de C7 |

**Égalité** : si les intervalles de Wilson se chevauchent, les approches sont jugées **équivalentes**. A est alors gardée, car elle ne fait sortir aucune donnée du poste, fonctionne hors ligne et ne coûte rien. E n'est retenue que si elle supprime des fausses alertes de A **sans en perdre une vraie**.

### 4.7 Mesure « deux points choisis » (C12), ajoutés le 2026-11-13 avant l'essai

Idée de l'utilisateur : il choisit deux points du corps, et si le segment qui les relie raccourcit par rapport à la calibration, il est affaissé. Mesure : longueur du segment ÷ largeur des épaules, comme les autres mesures.

**Candidats** :
- les repères MediaPipe 0 à 16 (visage, épaules, coudes, poignets) ;
- 23 et 24 (hanches) s'ils sont visibles sur plus de 90 % des images ;
- le haut de la tête estimé ;
- le milieu des épaules.

Outil : `essais/scanner_paires.py`, sur les enregistrements de repères faits sur un bureau.

| ID | Critère pour qu'une paire soit valable |
|----|----------------------------------------|
| C12a | Il existe **un seul seuil** auquel tête en avant et avachi sont signalés sur ≥ 90 % des images, et droit2 et clavier sur ≤ 10 %, **dans chaque enregistrement de bureau** |
| C12b | Bruit immobile (écart-type sur « droit ») sous le tiers de ce seuil (comme CA3) |

### 4.8 Repères sur le buste (C13), ajoutés le 2026-11-13 avant l'essai

Constat du 2026-11-13 : en s'avachissant, tout le haut du corps descend dans l'image, tête comprise. Les mesures tête-épaules ne le voient pas, et la descente des épaules confond l'avachi avec le regard vers le clavier. MediaPipe ne donne aucun repère entre les épaules et les hanches, et les hanches sont hors champ.

Idée de l'utilisateur : des repères **le long du buste**. On place des points virtuels sur le vêtement, sous la ligne des épaules, à 0,25, 0,5, 0,75 et 1 largeur d'épaules, au centre et à ±0,25 largeur. On les suit d'une image à l'autre par flux optique (calcul local, aucune image gardée : compatible C7).

Le point du haut est **sur le front** (précision de l'utilisateur) : milieu des yeux, remonté de 0,8 écart d'yeux le long de l'axe du visage.

**Mesures, par rapport à la calibration**, toutes divisées par la largeur des épaules :
- (a) raccourcissement de la ligne front → repères du buste, moyenne sur les repères suivis (mesure principale, l'idée de l'utilisateur) ;
- (b) raccourcissement épaules → repères du buste ;
- (c) descente des repères dans l'image.

Outil : `essais/reperes_buste.py`, sur les photos des enregistrements de bureau A et B. La référence est droit_0 ; les autres photos sont prises toutes les 2 s.

| ID | Critère pour qu'une mesure soit valable |
|----|------------------------------------------|
| C13a | Un seul seuil auquel avachi et tête en avant sont signalés sur ≥ 90 % des photos, et droit2 et clavier sur ≤ 10 %, **dans A et dans B** |
| C13b | Écart-type sur les photos « droit » sous le tiers de ce seuil |
| C13c | Repères suivis (flux optique réussi) sur ≥ 80 % des photos de bonne posture |

Ce n'est qu'un essai sur photos (6 par posture). Une mesure valable devra ensuite être confirmée sur un **nouvel** enregistrement, en continu (`rejouer.py`), avant d'entrer dans l'application.

*Résultat sur photos (2026-11-13) : C13c non atteint.* Les repères ne sont retrouvés que sur 14 des 34 photos de bonne posture : t-shirt uni sans motif, 2 s entre deux photos, et dans A la plupart des repères tombent sous le bord de l'image. L'essai sur photos ne permet donc pas de juger l'idée.

*Essai en continu, ajouté le 2026-11-13 avant l'enregistrement.* `enregistrer.py` pose les repères au début de la calibration de « droit », sur les points du buste faciles à suivre (plis, col, coutures ; jusqu'à 30), puis les suit image par image. Seules leurs positions sont écrites. Les critères C13a, C13b et C13c s'appliquent **image par image**, comme au banc, sur de **nouveaux** enregistrements de bureau.

*Résultat en continu (enregistrement C, 2026-11-13) : C13c non atteint, piste écartée sous cette forme.* Les 30 repères restent tous suivis pendant « droit ». Au premier changement de posture, il n'en reste que 5, puis 1 à partir de la tête en avant. Un t-shirt uni se déforme et se plisse quand on bouge : le flux optique perd ses points, et un point perdu ne peut pas être retrouvé sans recalibrer. Bonnes postures suivies : 24 % des images.

*Essai avec gommettes, ajouté le 2026-11-13 avant l'enregistrement.* 2 ou 3 gommettes d'une couleur vive (vert, rose ou bleu) sont collées sur le buste et retrouvées par leur couleur sur chaque image, dans la zone du buste (`enregistrer.py --gommettes <couleur>`). Les mesures (a), (b) et (c) et les critères C13a, C13b et C13c ne changent pas. Une image compte comme suivie si **toutes** les gommettes vues à la calibration sont retrouvées. Enregistrement neuf : `2026-11-13-bureau-d`.

### 4.9 Vidéos générées (C14), ajoutés le 2026-11-13 avant l'essai

Idée de l'utilisateur : générer des **vidéos** plutôt que des photos. On anime l'image « droit » d'une personne générée (modèle image → vidéo du routeur HF). Le cadrage reste celui de l'image de départ, et le mouvement est continu : on peut donc noter les vidéos au banc, image par image, et suivre les repères du buste. Calibration : l'image de départ, qui est aussi la 1re image de chaque vidéo. Outil : `essais/generer_videos.py`.

Sonde : une personne (n° 1), 3 vidéos (témoin immobile, avachi, tête en avant).

| ID | Critère |
|----|---------|
| C14a | MediaPipe voit tête et épaules sur ≥ 90 % des images de chaque vidéo |
| C14b | Témoin : écarts à la calibration sous le tiers des seuils de l'application (raccourcissement < 1 %, cou < 2°, largeur < 8,3 %) sur ≥ 90 % des images. C'est la preuve que la caméra ne bouge pas |
| C14c | Avachi et tête en avant : sur la dernière seconde, raccourcissement au-dessus du seuil de l'application (3 %) sur ≥ 90 % des images |

Sonde réussie : on génère les 16 personnes et on relance les bancs (C1, C2, C13). Comme pour le VLM, un résultat sur vidéo générée doit ensuite être confirmé sur un vrai enregistrement.

*Résultat (2026-11-13) : C14 non atteint, piste écartée.* Deux modèles ont été essayés, avec 3 vidéos de 5 s chacun. Pour LTX-2, la consigne « avachi » a été reformulée (« penché en avant sur le bureau »), puisque Wan2.2 avait fait se renverser la personne en arrière. Les critères n'ont pas changé.

| Modèle | Témoin (C14b) | Avachi (C14c) | Tête en avant (C14c) |
|--------|---------------|---------------|----------------------|
| Wan2.2-I2V-A14B | ❌ hochements de tête, raccourcissement jusqu'à 3,2 % (au-dessus du seuil même) | ❌ la personne se renverse en arrière, la caméra recule | ✅ formellement, mais tout le buste avance (épaules +27 % : « trop près ») |
| LTX-2 | ❌ zoom de la caméra (épaules +17 %) | ❌ scène inventée : personne debout, penchée sur un autre bureau | ❌ zoom jusqu'à ne plus voir que les yeux (MediaPipe perd les épaules) |

Les modèles vidéo ne gardent ni le cadrage, ni la personne, ni le geste demandé avec la précision dont les seuils ont besoin (3 % de raccourcissement).

*2e sonde, modèles chinois (2026-11-13).* Nouvelles consignes : caméra, corps et geste séparés, plus un prompt négatif. Critères inchangés.
- UniAnimate-DiT (animation guidée par squelettes), SkyReels-V1 et HunyuanVideo-I2V sont annoncés sur le routeur, mais répondent « 404 » chez fal-ai.
- MiniMax-H3-Turbo répond « Model not supported by provider wavespeed ».

| Modèle | Témoin (C14b) | Avachi (C14c) | Tête en avant (C14c) |
|--------|---------------|---------------|----------------------|
| Wan2.1-I2V-14B-720P (wavespeed) | ✅ raccourcissement ≤ 0,7 % | ✅ formellement, mais caricature : tête posée sur le bureau, puis un écran apparaît devant | ❌ rien ne bouge (0,8 %) |
| Wan2.2-I2V-A14B, consignes v2 | ❌ dérive de 2,2 % | ✅ formellement, même caricature (front sur le bureau) | ✅ formellement (buste qui avance) |

Aucun modèle ne réussit les 3 vidéos : **C14 non atteint, piste écartée.** De plus, les « avachis » réussis sont des caricatures (raccourcissement > 100 %, la tête passe sous la ligne des épaules), alors que les vrais avachis de l'utilisateur raccourcissent de 1,6 à 4 %. Un jeu fait de postures exagérées surestimerait l'application, comme le jeu d'images avait surestimé les VLM (16/16 contre 8/9).

Les paires valables sont classées par marge (écart entre la pire mauvaise posture et la pire bonne posture), en unités de bruit. La paire proposée par défaut doit avoir une marge **au moins égale** à celle de la mesure actuelle (haut de la tête → épaules). Sinon, la mesure actuelle reste par défaut.

---

## 5. Comment faire les essais

### 5.1 Préparation
- Webcam face à vous, à hauteur d'écran. **Cadrage** : tête et épaules entières dans l'image, avec les épaules **au-dessus des trois quarts de la hauteur**. Trop bas, MediaPipe devient instable.
- Éclairage de face, pas de contre-jour.
- **Arrêtez l'assistant** (menu de l'icône → Quitter) pour libérer la webcam.
- Notez la date, la machine, la webcam et les réglages utilisés.

### 5.2 Essai guidé et banc d'essai

1. **Enregistrer** (environ 3 min, à faire assis à son poste) :
   ```powershell
   .\.venv\Scripts\python essais\enregistrer.py essais\donnees\2026-10-30
   ```
   - Une fenêtre s'affiche au premier plan : cliquez dessus, puis appuyez sur **ESPACE**.
   - Suivez les 10 consignes : 4 s pour se placer, puis 12 s d'enregistrement chacune.
   - Seuls les 33 repères MediaPipe (des nombres) sont écrits, dans `landmarks.jsonl`. Le dossier `essais/donnees/` est exclu de git.

2. **Rejouer** dans la vraie logique de détection, avec les réglages par défaut :
   ```powershell
   .\.venv\Scripts\python essais\rejouer.py essais\donnees\2026-10-30\landmarks.jsonl
   ```
   - La calibration est faite sur les secondes 4 à 7 de « droit ».
   - Le banc applique le même lissage, la même hystérésis et le même délai d'alerte que l'application.
   - Il affiche pour chaque posture : % d'images signalées, % avec le bon motif, nombre d'alertes, puis le verdict C1/C2.

3. **Comparer** au tableau du § 6. Une modification de la détection n'est acceptée que si elle ne fait échouer aucun critère qui passait.

Les deux scripts sont des outils de mesure, pas des tests unitaires. Les tests automatiques (`pytest`, 48 tests) vérifient la logique avec des postures simulées.

### 5.3 Essais manuels dans l'application

| Essai | Procédure | Attendu |
|-------|-----------|---------|
| Calibration | Calibrer immobile, puis recalibrer en bougeant | « Calibration enregistrée », puis « Calibration refusée : vous avez bougé » |
| Signalement | Bouton « Tester le signalement » | Liseré puis pastille 6 s, clics traversants, focus conservé |
| Écrans multiples (C6) | Calibrer face à l'écran 1 ; se tourner vers l'écran 2, « Ajouter un écran » ; alterner 1 min | Pas d'alerte ; la page indique « écran 1 / écran 2 » |
| Lieux | Créer « Maison », calibrer, revenir à « Bureau » par le menu de l'icône | Chaque lieu garde ses calibrations |
| Hors champ / pause / webcam occupée (C5) | Sortir du champ ; Pause ; ouvrir l'application Caméra | Gris, sans alerte ; reprise seule à la fermeture de l'application Caméra |
| Coach | Après quelques minutes suivies : onglet **Rapport IA** → « Générer mon rapport » | Rapport en 4 parties, ou un message clair si le token est absent ou invalide |
| Performance (C3) | Assistant actif 30 s, mesurer le temps processeur du processus | ≤ 5 % de la machine, ≤ 500 Mo |

### 5.4 Essai « webcam déplacée » (C8)

À faire avec un **ordinateur portable** (webcam intégrée à l'écran), assis à son poste, environ 3 min.

1. **Enregistrer** :
   ```powershell
   .\.venv\Scripts\python essais\enregistrer_camera.py essais\donnees\AAAA-MM-JJ-camera
   ```
   Cliquez sur la fenêtre, puis **ESPACE**. Pour chaque étape, vous avez 8 s pour faire le geste et vous rasseoir droit, puis 10 s d'enregistrement **en restant droit** (sauf à l'étape « avachi ») :

   | Étape | Consigne |
   |-------|----------|
   | reference | Rester droit, ne rien toucher (sert de calibration) |
   | incline_arriere | Incliner l'écran d'environ 10° vers l'arrière |
   | incline_avant | Incliner l'écran d'environ 10° vers l'avant (par rapport au départ) |
   | retour | Remettre l'écran comme au départ |
   | tourne | Tourner l'ordinateur d'environ 10° sur le bureau |
   | deplace | Déplacer l'ordinateur d'environ 10 cm (reculer ou décaler) |
   | lumiere | Changer l'éclairage (lampe, rideau), sans toucher l'ordinateur |
   | avache | S'avachir, sans toucher l'ordinateur |

   Sont écrits **uniquement des nombres** : les 33 repères MediaPipe, et pour chaque image le décalage estimé du décor (déplacement, rotation, échelle, nombre de points retrouvés). Aucune image n'est enregistrée.

2. **Analyser** :
   ```powershell
   .\.venv\Scripts\python essais\analyser_camera.py essais\donnees\AAAA-MM-JJ-camera\camera.jsonl
   ```
   Pour chaque étape : décalage du décor, écart des épaules sans compensation, écart résiduel avec compensation, part des images où la compensation est possible, verdict C8a à C8d.

### 5.5 Essai VLM sur photos réelles (confirmation de C9)

Les résultats du § 6.5 viennent d'images générées. Cet essai les confirme ou les écarte. Les critères restent ceux du § 4.4 : sur 12 photos positives et 48 négatives, il faut **au moins 11/12 reconnues** et **au plus 2/48 excusées à tort**.

**Préparation (2 min)**
- Quitter l'assistant (icône → Quitter), sinon la webcam est prise.
- À portée de main : **un vrai téléphone** et **une vraie tasse** (pleine ou non).
- Cadrage habituel : ordinateur à sa place, éclairage de tous les jours. Ne pas « soigner » la scène, on veut des conditions réelles.
- Les photos partent chez les fournisseurs du routeur Hugging Face : n'enregistrer que soi, ou quelqu'un qui a donné son accord.

**Enregistrement (environ 3 min)**, sans `--etape`, pour avoir les 10 postures :
```powershell
.\.venv\Scripts\python essais\enregistrer.py essais\donnees\2026-11-06-reel --photos
```
Cliquer dans la fenêtre, puis ESPACE. Pour chaque posture : 6 s de préparation (consigne en orange), puis 12 s d'enregistrement (en vert), avec une photo toutes les 2 s. **Prendre la posture pendant la préparation et ne plus bouger une fois en vert**, jusqu'à la consigne suivante.

Cet enregistrement sert **aussi d'essai de validation de la détection** (C1, C2), en attente depuis le 2026-10-30 : `landmarks.jsonl` est écrit en même temps que les photos.

| Posture | Consigne | Point d'attention |
|---------|----------|-------------------|
| droit, droit2 | Assis droit, face à l'écran | Mains loin du visage |
| tete_avant | Tête vers l'écran, dos immobile | **Négatif le plus important** : le VLM ne doit pas l'excuser |
| clavier, avache, penche, trop_pres | Comme d'habitude | Pas d'objet en main |
| menton_main | Menton dans la main | Main vide : c'est un piège pour le VLM |
| telephone | **Vrai téléphone** à l'oreille, en gardant la tête comme d'habitude (si on la penche, tant mieux : c'est le cas réel) | Téléphone visible, pas caché par la main |
| boire | **Boire vraiment** dans la tasse, à son rythme | Tasse visible à la bouche |

**Vérification à l'œil (1 min)** : ouvrir `essais\donnees\2026-11-06-reel\photos\`. Supprimer une photo « telephone_* » ou « boire_* » seulement si l'objet n'y est pas, par exemple prise pendant le geste. Noter combien ont été supprimées. Ne pas utiliser `valider_images.py` : ses contrôles (témoin droit2 notamment) sont faits pour les images générées.

**Comparaison** : les 2 modèles retenus, plus les 2 à la limite, soit environ 240 appels :
```powershell
.\.venv\Scripts\python essais\comparer_vlm.py essais\donnees\2026-11-06-reel --modeles google/gemma-4-26B-A4B-it,Qwen/Qwen3-VL-30B-A3B-Instruct,Qwen/Qwen3.5-9B,Qwen/Qwen3-VL-235B-A22B-Instruct
```

**En plus, sans frais** : les mêmes postures dans le banc de détection, pour voir combien de fois le téléphone et la boisson déclenchent l'alerte, c'est-à-dire le problème que le VLM doit corriger :
```powershell
.\.venv\Scripts\python essais\rejouer.py essais\donnees\2026-11-06-reel\landmarks.jsonl
```

**Décision**
- C9 atteint par au moins un modèle : on passe à l'intégration (option désactivée par défaut, accord explicite, photo envoyée seulement au moment de l'alerte « tête »).
- Sinon : piste écartée, résultats notés au § 6.3.

### 5.6 Banc complet, à relancer avant et après chaque modification (C4, C9, C10)

Le jeu généré reste sur le disque (`essais/donnees/genere/`, exclu de git) : relancer le banc ne coûte que les appels VLM, et les résultats restent comparables d'une version à l'autre.

```powershell
# 1. Jeu généré : générer, trier ; relancer les deux pour remplacer les rejets (au plus 2 fois)
.\.venv\Scripts\python essais\generer_images.py essais\donnees\genere
.\.venv\Scripts\python essais\valider_images.py essais\donnees\genere
# 2. Détection (application) : essais réels et séries générées, total d'échecs à comparer
.\.venv\Scripts\python essais\images_vers_reperes.py essais\donnees\genere
.\.venv\Scripts\python essais\rejouer.py essais\donnees\2026-10-30\landmarks.jsonl "essais\donnees\genere\serie_*\landmarks.jsonl"
# 3. VLM téléphone / boisson (C9)
.\.venv\Scripts\python essais\comparer_vlm.py essais\donnees\genere
# 4. Tests automatiques (C4)
.\.venv\Scripts\python -m pytest -q
```

---

## 6. Résultats

### 6.1 Banc d'essai du 2026-10-30

Une personne, une séance, Windows 11, webcam intégrée, réglages par défaut (épaules 5 %, tête 5 %, inclinaison 10 %, distance 25 %, main 2,0, délai 2 s). Environ 360 images par posture.

| Posture | Attendu | Images signalées | Bon motif | Alertes | C-alerte | C-images |
|---------|---------|------------------|-----------|---------|----------|----------|
| Droit (début) | aucune | 27 % | — | 0 | ✅ | ❌ |
| Tête en avant | tête | 100 % | 100 % | 1 | ✅ | ✅ |
| Regard clavier | aucune | 100 % | — | 1 | ❌ | ❌ |
| Avachi | épaules | 100 % | 86 % | 1 | ✅ | ❌ |
| Penché / accoudé | inclinaison | 100 % | 100 % | 1 | ✅ | ✅ |
| Menton dans la main | main | 99 % | 97 % | 1 | ✅ | ✅ |
| Trop près | distance | 100 % | 100 % | 1 | ✅ | ✅ |
| Droit (fin) | aucune | 19 % | — | 0 | ✅ | ❌ |
| Téléphone | non noté | 100 % (tête en avant) | — | 1 | — | — |
| Boire | non noté | 100 % | — | 1 | — | — |

**11 critères sur 16 atteints.** Toutes les mauvaises postures déclenchent une alerte, et la posture droite n'en déclenche aucune.

Les échecs :
- **Regard vers le clavier** : les épaules descendent de 4,4 %, ce qui provoque une fausse alerte « épaules affaissées ».
- **Posture droite** : les épaules descendent naturellement d'environ 5 % en quelques secondes. La posture est donc signalée 19 à 27 % du temps, mais jamais assez longtemps pour déclencher une alerte.
- **Avachi** : le motif « épaules » n'apparaît que sur 86 % des images ; sur les autres, seule la tête est signalée.

Les cas **téléphone** et **boisson** déclenchent « tête en avant ». La géométrie ne peut pas les distinguer, car les mains sont hors champ ou cachées.

### 6.2 Autres résultats

| Critère | Résultat | Statut |
|---------|----------|--------|
| C3 Performance | 1,3 % de la machine (28 % d'un cœur sur 22), 307 Mo, 10 images/s | ✅ |
| C4 Tests | 48 réussis, 1 ignoré (spécifique au Mac) | ✅ |
| C5 Hors champ / pause / webcam | Implémenté et couvert par les tests ; pas encore vérifié à la main en 0.4.0 | 🟡 à faire |
| C6 Écrans multiples | Vérifié uniquement par les tests automatiques (postures simulées) | 🟡 à faire |
| C7 Vie privée | Aucune image écrite ni envoyée ; le coach envoie 8 nombres | ✅ |

### 6.3 Pistes testées et écartées (preuves dans SUIVI_DEVELOPPEMENT.md)

| Piste | Résultat | Décision |
|-------|----------|----------|
| Profondeur, Depth Anything V2 Small (Hugging Face) | Ne sépare pas mieux la tête en avant que la mesure 2D ; 2,3 s par image | Écartée |
| VLM sur silhouette, Qwen3.8-27B (Hugging Face) | 7 réponses justes sur 30 (le hasard) ; téléphone jamais reconnu | Écartée |
| Points supplémentaires de MediaPipe | Seule la distance main-visage apporte une détection nouvelle (menton dans la main : 24-33 % → 97 %) | **Retenue** |
| Mesure des épaules rendue insensible à la distance à la caméra (par rapport au centre de l'image) | Sépare moins bien l'avachissement, confond davantage le clavier | Écartée |
| Images générées (Qwen-Image puis modification de la même image) pour noter tête en avant, avachi, trop près, clavier, penché | Qwen-Image-Edit : une image « inchangée » déplace le corps de 16,5 % (seuil 3 %) et altère les couleurs. FLUX.1-Kontext : stable (0,4 %) mais ne produit ni tête en avant ni avachi ni penché (3,9° contre 6°) | Écartée pour ces postures ; gardée pour téléphone, boisson, menton dans la main (C9, robustesse MediaPipe) |
| VLM pour recalibrer selon les cas | Non retenu sans essai : un VLM ne mesure pas des écarts de quelques %, et le déplacement de la caméra est un problème géométrique (voir F13) | Écartée au profit de F13 |
| VLM téléphone / boisson sur photo (C9, 2026-11-06) | 16/16 sur images générées, mais 8/9 au mieux sur photos réelles ; ratés : téléphone caché par la main | Écartée (règle du § 5.5) |
| VLM ou LLM à la place de MediaPipe pour la posture (C11, 2026-11-13) | 4 modèles, 3 façons de les interroger, 118 photos : soit 65 à 79 % de fausses alertes, soit la moitié des mauvaises postures ratées. Coût de 0,02 à 0,24 $/h, photos envoyées hors du poste | Écartée (§ 6.6) |
| MediaPipe, puis VLM qui confirme l'alerte (C11) | Fausses alertes 11 → 5, mais 5 vraies alertes perdues sur 26 | Écartée |
| Segment entre deux points choisis par l'utilisateur (C12) | 55 paires testées sur 4 séances : aucune ne sépare l'avachi des bonnes postures | Écartée (pas de listes déroulantes dans l'application) |
| Détection « épaules affaissées » activée (slouch) | Avachi vu dans 1 séance sur 3, mais clavier signalé (56 % et 99 %). Épaules qui se resserrent ou avancent en profondeur (z) : pas mieux (`essais/sonde_epaules.py`) | **Retirée** (2026-11-13) |
| Repères suivis sur le buste, ligne front → buste (C13) | Points perdus au premier changement de posture (t-shirt uni) : 24 % des images mesurables | Écartée sous cette forme ; essai avec gommettes prêt, non enregistré |
| Vidéos générées (Wan2.1, Wan2.2, LTX-2) au lieu de photos (C14) | Caméra qui zoome, personne qui change, avachis caricaturaux (> 100 % de raccourcissement, contre 2 à 4 % en vrai) | Écartée |

### 6.4 Webcam déplacée (C8), essai n° 1 du 2026-10-30

Portable, webcam intégrée ; 108 points du décor retrouvés par image (médiane).

| Étape | Décalage du décor (vertical) | Épaules sans compensation | Épaules avec compensation | Critère |
|-------|------------------------------|---------------------------|---------------------------|---------|
| Écran incliné vers l'arrière | +14,9 % | +29,0 % | −6,1 % | C8a ❌ |
| Écran incliné vers l'avant | −25,7 % | −54,8 % | +3,3 % | C8a ❌ |
| Écran remis | +1,1 % | +7,5 % | +5,1 % | C8a ❌ |
| Ordinateur tourné (~6°) | +0,8 % | +1,1 % | −0,7 % (54 % des images ≤ 2,5 %) | C8a ❌ |
| Ordinateur déplacé | +1,8 % (échelle 0,93) | +4,1 % | +3,8 % | C8b ❌ |
| Éclairage, avachi | — | — | — | C8c, C8d non évaluables (voir ci-dessous) |

**Verdict : critères C8 non atteints.**

Ce que l'essai montre malgré tout :
- **La compensation corrige l'essentiel de l'erreur due à la caméra** : 29 % → 6 % et 55 % → 3 % pour l'écran incliné. Sans elle, l'assistant serait inutilisable après chaque inclinaison.
- **La mesure du décor est stable** : à l'intérieur d'une étape, elle varie de moins de 0,6 %.

**Défauts du protocole n° 1**, à corriger avant de conclure :
1. Pour bouger l'ordinateur, l'utilisateur se lève ou se penche, puis se rassoit **un peu différemment**. À l'étape « écran remis », le décor est revenu à 1 % près, mais les épaules sont 7,5 % plus bas et le rapport tête-épaules a changé de 7,6 %. L'écart résiduel mélange donc l'erreur de compensation et le changement réel de posture : il ne mesure pas la compensation seule.
2. C8c (éclairage) et C8d (avachi) comparaient le décor à la **référence** au lieu de l'étape **précédente**. Or l'ordinateur avait été déplacé entre-temps : ces deux étapes ne sont pas évaluables.

**Protocole n° 2 (à faire)** : le buste reste immobile **pendant** le mouvement. On incline l'écran lentement d'une main, sans bouger le corps, pendant l'enregistrement. On mesure alors, à l'intérieur d'une même étape, si la position des épaules suit exactement la prédiction faite à partir du décor (pente proche de 1 et écart-type résiduel faible). C8c et C8d seront comparés à l'étape précédente. **Les critères restent ceux du § 4.3.**

### 6.5 Jeu généré et VLM téléphone / boisson (C9, C10), 2026-11-06

**Confirmation sur photos réelles (§ 5.5) : C9 non atteint.** Essai `essais/donnees/2026-11-06-reel`, 58 photos : 9 positives (6 téléphone, 3 boisson ; 4 photos « boire » écartées à l'œil, verre absent ou flou) et 49 négatives.

| Modèle | C9a reconnus (≥ 90 %) | C9b excusés à tort (≤ 5 %) | C9c latence | Verdict |
|--------|-----------------------|----------------------------|-------------|---------|
| Qwen/Qwen3-VL-30B-A3B-Instruct | 8/9 (89 %) | 0/49 | 2,5 s | ❌ |
| Qwen/Qwen3-VL-235B-A22B-Instruct | 8/9 (89 %) | 0/49 | 1,5 s | ❌ |
| google/gemma-4-26B-A4B-it | 7/9 (78 %) | 0/49 | 1,2 s | ❌ |
| Qwen/Qwen3.5-9B | 7/9 (78 %) | 0/49 | 1,0 s | ❌ |

- Toutes les erreurs portent sur le **téléphone caché par la main** (seule une main sur la joue est visible), c'est-à-dire le cas réel. Les boissons sont toutes reconnues.
- Aucune vraie mauvaise posture n'est excusée (0/49, tête en avant comprise).
- Dans cet essai, le téléphone ne déclenche **aucune alerte** de la détection : il n'y avait pas de fausse alerte à corriger.
- 9 photos positives, c'est peu : une seule erreur coûte 11 points.

Ci-dessous, les résultats sur images générées, qui ne sont donc **pas confirmés**.

**Jeu (C10)** : 8 personnes variées × 5 photos = 40 photos générées.
- 1er tri : 13 rejets, dont 5 tasses rejetées à tort par EfficientDet-Lite0 (outil remplacé par Lite2, voir § 4.5).
- 2 relances de « générer → valider » : **37 photos valables sur 40**, MediaPipe voit tête et épaules sur les 37.
- 3 trous restent : droit2_3 (la modification déplace le corps à chaque essai), menton_main_5 et menton_main_7 (main sous le menton, plus loin que le seuil, ou objet vu dans la main).
- Défaut non couvert par C10 : chez 4 personnes, le générateur a ajouté une interface de visio ou un écran au premier plan. Aucun biais mesuré : pas de faux « téléphone » sur ces personnes chez les modèles retenus.

**VLM (C9)**, 16 photos positives (téléphone, boisson), 21 négatives (droit, droit2, menton_main) :

| Modèle | C9a reconnus | C9b excusés à tort | C9c latence médiane | Verdict |
|--------|--------------|--------------------|---------------------|---------|
| google/gemma-4-26B-A4B-it | 16/16 | 0/21 | 1,2 s | ✅ |
| Qwen/Qwen3-VL-30B-A3B-Instruct | 16/16 | 0/21 | 2,5 s | ✅ |
| Qwen/Qwen3.5-9B | 16/16 | 1/21 (menton_main_2) | 1,1 s | ✅ (à la limite : 4,8 %) |
| Qwen/Qwen3-VL-235B-A22B-Instruct | 16/16 | 1/21 (menton_main_2) | 1,8 s | ✅ (à la limite) |
| zai-org/GLM-4.6V-Flash | 12/16 | 1/21 | 3,7 s | ❌ (7 erreurs 429 : fournisseur surchargé) |
| google/gemma-3-4b-it | 15/16 | 20/21 | 1,1 s | ❌ (répond « téléphone » presque partout) |

- **Reproductibilité** : 2e passe identique pour gemma-4-26B et Qwen3-VL-30B, soit 37 réponses sur 37 (température 0).
- **Banc de détection** : enregistrement réel inchangé (1 échec, le clavier) ; séries générées sans échec. Ce dernier résultat **ne prouve rien** : droit2 est retenu par le tri justement parce qu'il bouge moins que le tiers du seuil. Information utile tout de même : sur ces images, le téléphone ne déclenche une alerte que chez 2 personnes sur 8, alors que sur l'enregistrement réel il en déclenche toujours une (on baisse la tête en vrai). Le générateur ne reproduit pas ce mouvement.

### 6.6 MediaPipe, VLM ou LLM ? (C11), 2026-11-13

**Jeu** : enregistrements de bureau A et B, soit 118 photos notées. droit_0 sert de référence et n'est pas notée.
- Tâche principale : 36 photos de mauvaise posture (tête en avant, avachi, penché) et 34 de bonne posture (droit, droit2, clavier).
- Motif : 5 classes, sur 94 photos.

Toutes les réponses ont été demandées 2 fois (température 0). Détail : `essais/donnees/comparaison.json` ; outil : `essais/comparer_approches.py`.

| | Approche | Modèle | Mauvaises postures détectées (C11a) [IC 95 %] | Fausses alertes (C11b ≤ 10 %) [IC 95 %] | Motif juste | Latence médiane / p95 | Coût à 1 analyse / 5 s | Stabilité 2e passe | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| A | MediaPipe + seuils | MediaPipe Pose | 26/36, 72 % [56-84] | 11/34, 32 % [19-49] | 51 % | 0,06 s (local) | 0 | identique | référence |
| B | VLM, photo seule | Qwen3-VL-30B | 24/36, 67 % [50-80] | 16/34, 47 % [31-63] | 44 % | 1,3 / 5,5 s | 0,04 $/h | 94 % | ❌ C11a, C11b |
| B | VLM, photo seule | gemma-4-26B | 14/36, 39 % [25-55] | 1/34, 3 % [1-15] | 49 % | 1,1 / 1,6 s | 0,02 $/h | 100 % | ❌ C11a |
| C | VLM, référence + photo | Qwen3-VL-30B | 33/36, 92 % [78-97] | 25/34, 74 % [57-85] | 46 % | 1,8 / 5,2 s | 0,06 $/h | 86 % | ❌ C11b |
| C | VLM, référence + photo | gemma-4-26B | 17/36, 47 % [32-63] | 3/34, 9 % [3-23] | 49 % | 1,8 / 3,0 s | 0,04 $/h | 98 % | ❌ C11a |
| D | LLM, repères (texte) | Qwen3.8-27B | 33/36, 92 % [78-97] | 22/34, 65 % [48-79] | 46 % | 1,2 / 2,0 s | 0,12 $/h | 100 % | ❌ C11b |
| D | LLM, repères (texte) | gpt-oss-120b | 35/36, 97 % [86-100] | 27/34, 79 % [63-90] | 20 % | 0,5 / 1,3 s | 0,24 $/h | 96 % | ❌ C11b |
| E | MediaPipe, puis VLM qui confirme | Qwen3-VL-30B | 21/36, 58 % | 5/34, 15 % | 51 % | 1,3 s par alerte | 1 appel par alerte | — | ❌ perd 5 vraies alertes |
| E | MediaPipe, puis VLM qui confirme | gemma-4-26B | 14/36, 39 % | 0/34, 0 % | 51 % | 1,1 s par alerte | 1 appel par alerte | — | ❌ perd 12 vraies alertes |

**Lecture** :
- **Aucune approche ne remplit C11.** Les modèles qui détectent plus que MediaPipe (C et D, à 92-97 %) le font en signalant presque tout : 65 à 79 % de fausses alertes. Ceux qui restent sobres (gemma-4) ratent la moitié des mauvaises postures. Aucun ne sépare mieux les deux groupes : leurs intervalles chevauchent ceux de A ou les dépassent du mauvais côté.
- **Le motif est mal reconnu par tous**, A compris (20 à 51 %). « Penché » et « menton dans la main » se confondent souvent avec « trop près » et « affaissé ».
- **L'hybride E** réduit bien les fausses alertes de A (11 → 5 avec Qwen3-VL), mais au prix de 5 vraies alertes perdues sur 26.
- **Coût et confidentialité** : à une analyse toutes les 5 s, les modèles du routeur coûtent de 0,02 à 0,24 $ par heure, soit 0,2 à 2 $ par journée de travail et par personne. Ils font sortir une photo (B, C, E) ou des repères (D) toutes les 5 s, ce que C7 interdit par défaut. Leur latence (p95 jusqu'à 5,5 s) dépend du réseau et du fournisseur. MediaPipe tourne en local, hors ligne, en 0,06 s, gratuitement.
- **MediaPipe photo par photo (32 % de fausses alertes) n'est pas l'application.** L'application lisse sur 1 s, attend 2 s avant d'alerter et se calibre sur 3 s, pas sur une seule photo. Au banc en continu, l'enregistrement C ne donne aucune alerte en bonne posture (§ ci-dessous). La comparaison reste équitable, puisque toutes les approches voient les mêmes photos, avec la même référence.

**Décision : MediaPipe est gardé seul pour la détection.** Les VLM et LLM sont écartés pour la posture (§ 6.3). Le LLM reste utile pour ce qu'il fait déjà : le bilan du coach, à partir de 8 chiffres.

**Limites** : une seule personne, deux séances, 6 photos par posture. Les intervalles de confiance sont larges (± 15 points) : une différence de quelques photos ne veut rien dire.

**Banc en continu sur les 4 enregistrements de bureau** (`rejouer.py`, détections par défaut) :

| Enregistrement | droit, droit2, clavier | Tête en avant | Avachi | Penché (motif « lean ») | Échecs |
|---|---|---|---|---|---|
| 2026-10-30 | clavier 15 % (transitions, § 8) | ✅ | ✅ 98 % | ✅ | 1 |
| 2026-11-13 A | ✅ | 86 % | **0 %** | 9 % (accoudé) | 3 |
| 2026-11-13 B | droit2 32 % (calibration assise plus en arrière) | ✅ | **0 %** | 0 % (motif « posture ») | 3 |
| 2026-11-13 C | ✅ | ✅ 90 % | 71 % | ✅ 98 % | 1 |

Point faible confirmé : **l'avachi**. Sur 3 des 4 séances, la hauteur tête-épaules ne raccourcit presque pas (1,6 à 1,8 % dans A et B), parce que tout le haut du corps descend dans l'image, tête comprise.
- Aucune des 55 paires de points (C12) ne le sépare des bonnes postures sur les 4 séances, la mesure actuelle non plus (marge −0,055).
- La détection « épaules affaissées » le voit dans B, mais signale aussi le clavier.
- Les repères du buste n'ont pas pu être suivis sur le t-shirt (C13). L'essai avec gommettes est prêt (`enregistrer.py --gommettes`) mais n'a pas été enregistré.
- Les vidéos générées ne produisent pas d'avachi réaliste (C14).

---

## 7. Démo (environ 6 minutes)

**Préparation** :
- assistant lancé ;
- page http://127.0.0.1:8765 ouverte, avec l'aperçu webcam déplié ;
- cadrage vérifié (épaules au-dessus des trois quarts de l'image) ;
- token du coach enregistré ;
- quelques minutes de suivi déjà accumulées, pour que les statistiques et le coach aient de la matière.

| # | Action | Ce qu'on montre | Message |
|---|--------|-----------------|---------|
| 1 | Page de réglages, aperçu webcam | Squelette en direct, état « Posture correcte » | Tout est calculé sur l'ordinateur ; aucune image ne sort |
| 2 | **Recalibrer**, immobile 3 s | « Calibration enregistrée » | Puis recommencer en bougeant : « Calibration refusée » |
| 3 | S'avachir 3 s, puis tête en avant | Jauges qui passent à l'ambre, puis le **liseré** en haut de l'écran | Signal discret : pas de son, pas de fenêtre |
| 4 | Rester mal installé, ou cliquer sur **Tester le signalement** | La **pastille** « Redressez-vous » et son motif | Elle laisse passer les clics : on continue de travailler |
| 5 | Se pencher sur le côté, puis menton dans la main, puis se rapprocher de l'écran | Les motifs « Penché », « Tête appuyée sur la main », « Trop près » | Les 5 détections |
| 6 | Se tourner vers le 2e écran (déjà ajouté) | Pas d'alerte, « écran 2 » | Écrans multiples |
| 7 | Menu de l'icône → **Lieu de travail** → Maison | Changement de lieu en un clic | Pas de recalibration à chaque changement d'endroit |
| 8 | Onglet **Rapport IA** → **Générer mon rapport** | Rapport de journée de Qwen (Hugging Face) : bilan, postures, moments, conseils | Seuls 8 chiffres sont envoyés au LLM |
| 9 | Montrer le tableau du § 6 | 11 critères sur 16, les échecs expliqués | La démarche : mesurer, décider, puis vérifier |

**En cas de problème pendant la démo** :
- le signalement ne se déclenche pas → bouton « Tester le signalement » ;
- le coach est indisponible (réseau) → montrer le message d'erreur clair, puis la sortie de `mon_script.py` enregistrée à l'avance ;
- la webcam est occupée → fermer Teams ou Zoom : l'assistant reprend seul.

---

## 8. Prochaines améliorations, par critère visé

| Priorité | Amélioration | Critère visé |
|----------|--------------|--------------|
| 0 | **Webcam déplacée sans recalibrage (F13)**, puis lieu reconnu (F14) et dérive lente (F15), selon le résultat de l'essai § 5.4 | C8 |
| 1 | Regard vers le clavier. **Cause trouvée le 2026-11-06** : les 15 % d'images signalées sont toutes dans les transitions (1,3 s au début, en sortant de « tête en avant » ; 0,5 s à la fin). Le reste de la posture, environ 10 s, n'a aucune image signalée, et il n'y a aucune alerte. Correction du protocole, sans toucher aux critères ni à la détection : préparation portée de 4 à 6 s dans `enregistrer.py`. À confirmer avec l'enregistrement du § 5.5 | C1 clavier |
| 2 | Dérive naturelle : référence qui suit lentement l'utilisateur quand il est droit, ou tolérance épaules adaptée au bruit mesuré pendant la calibration | C1 images |
| 3 | Essais réels des écrans multiples et revérification de C5 en 0.4.0 | C5, C6 |
| 1 bis | **Avachi** : seule mauvaise posture encore ratée (0 % dans 2 séances sur 4). Prochain essai : gommettes sur le buste (`enregistrer.py --gommettes`, C13), ou mesure combinée « épaules qui descendent sans bascule de la tête », à fixer avant l'essai et à valider sur un nouvel enregistrement | C2 avachi |
| 4 | ~~Téléphone et boisson par VLM~~ : C9 non atteint sur photos réelles, piste écartée (§ 6.3). Reste possible : détection de mains avec MediaPipe Hands si elles sont dans le champ. **Pas de VLM local** (décision du 2026-11-06) | C9 (§ 4.4) |
| 5 | Essais sur d'autres personnes et d'autres webcams (les seuils actuels viennent d'une seule personne) | Validité de C1 et C2 |
