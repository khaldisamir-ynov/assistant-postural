# Dataset de test depuis une vidéo webcam

Une vidéo d’une personne assise à son bureau, face à sa webcam, devient un essai noté par `rejouer.py`. Le banc ne lit pas la vidéo : il lit `landmarks.jsonl`. Une fois ce fichier écrit, la vidéo se supprime.

La personne filmée est l’utilisateur, ou quelqu’un qui a accepté cet enregistrement. Pas de replay d’un tiers.

## 1. Vidéo acceptée

- Une seule personne, assise à un bureau, de face. Le profil, le canapé et l’ordinateur sur les genoux sont hors périmètre (spécifications, § 1).
- Webcam fixe à hauteur d’écran, même cadrage du début à la fin : pas de zoom, de coupe, ni de recadrage. Tête et épaules visibles en entier.
- Image telle que l’application la montre (effet miroir). Une capture brute OpenCV se retourne horizontalement avant MediaPipe, comme `essais/enregistrer.py`. Une vidéo déjà miroir ne se retourne pas une seconde fois.
- Lumière stable. Pas de bandeau, de chat, ni de caméra qui suit le visage.

## 2. Postures à tenir

Même ordre et mêmes durées que `enregistrer.py` : **6 s de préparation** (non écrites), puis **12 s tenues** (écrites). `t` repart à 0 à chaque posture et couvre les 12 s tenues.

| Code | Consigne pendant les 12 s | Noté par le banc |
|------|---------------------------|------------------|
| `droit` | Bien droit, immobile, face à l’écran | oui : aucune alerte |
| `tete_avant` | Tête vers l’écran, dos immobile | oui : motif `posture` |
| `clavier` | Yeux ou menton vers le clavier, dos droit | oui : aucune alerte |
| `avache` | Épaules qui tombent, dos qui s’arrondit | oui : motif `posture` |
| `penche` | Penché sur le côté, ou accoudé | oui : motif `lean` (`posture` admis en plus) |
| `droit2` | De nouveau bien droit, immobile | oui : aucune alerte |

`menton_main`, `telephone` et `boire` peuvent suivre, dans cet ordre, avec les mêmes 6 + 12 s. Le banc les affiche « non noté ».

La calibration est la médiane de `droit` pour `t` entre 4 s et 7 s. Pendant ces 3 s la personne est déjà droite et immobile. Un mouvement ici fausse tout l’essai.

## 3. Découpage

Si la vidéo a été tournée exprès, chaque posture est un bloc de 18 s (6 + 12) collé au suivant, dans l’ordre du tableau.

Si la vidéo existe déjà, noter à la main le début et la fin de chaque tenue, en secondes de fichier. Jeter la préparation et les transitions : les essais passés montraient que la première seconde après un changement de posture était comptée à tort comme une erreur. Il faut 12 s stables par code. Sans ces intervalles, le fichier passe dans le banc et les pourcentages sont faux.

## 4. Fichier produit

Dossier : `essais/donnees/AAAA-MM-JJ/` (ignoré par git). Une ligne JSON par image où MediaPipe voit la pose, uniquement pendant les 12 s :

```json
{"posture": "droit", "t": 4.1, "lm": [[0.5, 0.2, -0.1, 0.99]], "wh": [1280, 720], "buste": null}
```

- `posture` : un code du tableau.
- `t` : secondes depuis le début des 12 s, deux décimales.
- `lm` : 33 repères MediaPipe, chacun `[x, y, z, visibility]` normalisés (x, y, z à 4 décimales, visibilité à 3).
- `wh` : largeur et hauteur de l’image en pixels.
- `buste` : `null`, sauf si l’essai suit aussi les repères du buste.

Pose : `mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)`, image BGR passée en RGB. Une image sans pose n’est pas écrite.

## 5. Contrôle

Depuis la racine du projet, assistant arrêté :

```text
.venv\Scripts\python essais\rejouer.py essais\donnees\AAAA-MM-JJ\landmarks.jsonl
```

Critères (réglages par défaut) :

- `droit`, `droit2`, `clavier` : 0 alerte, au plus 10 % d’images signalées.
- `tete_avant`, `avache` : au moins 1 alerte, motif `posture` sur au moins 90 % des images, un autre motif sur 10 % au plus.
- `penche` : au moins 1 alerte, motif `lean` sur au moins 90 % des images. `posture` en plus n’est pas un échec.
- Bruit immobile (CA3) : sur `droit` après `t` = 7 s, l’écart-type de `posture` et de `lean` reste sous le tiers de leur tolérance.

La dernière ligne affiche le nombre de critères non atteints. `0` : l’essai entre dans le jeu de test.

Ensuite supprimer le `.mp4`. Ne garder que `landmarks.jsonl`.
