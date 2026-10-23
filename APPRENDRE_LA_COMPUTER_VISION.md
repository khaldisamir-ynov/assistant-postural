# Apprendre la computer vision avec l'Assistant de posture

> Guide destiné à un étudiant qui part de zéro. Objectif : qu'à la fin, vous compreniez **ce qu'est la computer vision**, **comment on construit un projet de ce type**, et **pourquoi chaque ligne de ce dépôt est écrite comme elle l'est**.
>
> Le fil conducteur est le projet de ce dépôt : une application qui regarde votre webcam et vous prévient quand vous vous avachissez. Il est petit (quelques centaines de lignes) mais il contient **tout le pipeline** d'un vrai produit de vision par ordinateur.

---

## Sommaire

1. [Qu'est-ce que la computer vision ?](#1-quest-ce-que-la-computer-vision-)
2. [Une image, pour un ordinateur, c'est quoi ?](#2-une-image-pour-un-ordinateur-cest-quoi-)
3. [Les grandes familles de problèmes](#3-les-grandes-familles-de-problèmes)
4. [Deux époques : vision « classique » et deep learning](#4-deux-époques--vision--classique--et-deep-learning)
5. [Le pipeline universel d'un projet de vision](#5-le-pipeline-universel-dun-projet-de-vision)
6. [La boîte à outils](#6-la-boîte-à-outils)
7. [Le projet, étape par étape](#7-le-projet-étape-par-étape)
   - 7.1 Capturer la webcam
   - 7.2 Préparer l'image (miroir, BGR → RGB)
   - 7.3 Le modèle : MediaPipe Pose
   - 7.4 Choisir les bons repères
   - 7.5 Transformer des points en mesures (géométrie)
   - 7.6 La calibration : apprendre « votre » bonne posture
   - 7.7 Décider : seuils et écarts
   - 7.8 Filtrer dans le temps
   - 7.9 Gérer les cas où ça ne marche pas
   - 7.10 Le budget CPU
   - 7.11 Afficher : squelette, JPEG, flux vidéo
   - 7.12 Tester de la vision sans webcam
8. [Le savoir-faire : les réflexes d'un ingénieur vision](#8-le-savoir-faire--les-réflexes-dun-ingénieur-vision)
9. [Limites et pièges de ce projet (et de la vision en général)](#9-limites-et-pièges-de-ce-projet-et-de-la-vision-en-général)
10. [Expériences à faire vous-même](#10-expériences-à-faire-vous-même)
11. [Pour aller plus loin](#11-pour-aller-plus-loin)
12. [Glossaire](#12-glossaire)

---

## 1. Qu'est-ce que la computer vision ?

La **computer vision** (vision par ordinateur) est la discipline qui consiste à faire **extraire de l'information utile à partir d'images ou de vidéos** par un programme.

« Information utile » dépend du besoin :

| Besoin | Information extraite |
|--------|----------------------|
| Déverrouiller un téléphone | « Ce visage est-il celui du propriétaire ? » |
| Voiture autonome | « Où sont les piétons, les voitures, les lignes ? » |
| Contrôle qualité en usine | « Cette pièce a-t-elle un défaut ? » |
| Lecture de chèques | « Quels chiffres sont écrits ici ? » |
| **Ce projet** | « Où sont les épaules et les oreilles de la personne, et bougent-elles par rapport à sa posture de référence ? » |

La difficulté fondamentale : pour un humain, voir est instantané et inconscient. Pour un ordinateur, une image n'est **qu'une grille de nombres**. Toute la discipline consiste à construire le pont entre cette grille de nombres et un concept (« une épaule », « un défaut », « une posture correcte »).

Il faut garder en tête une distinction importante :

- **Traitement d'image** : on transforme une image en une autre image (flouter, redresser, améliorer le contraste). L'entrée et la sortie sont des images.
- **Computer vision** : on transforme une image en **information** (des coordonnées, une classe, une décision). L'entrée est une image, la sortie est de la connaissance.

Ce projet fait les deux : un peu de traitement d'image (miroir, conversion de couleurs, dessin), et surtout de la vision (trouver les repères du corps, puis décider).

---

## 2. Une image, pour un ordinateur, c'est quoi ?

### 2.1 Une grille de pixels

Une image numérique est un **tableau à deux dimensions** de points appelés **pixels**. Une webcam standard produit par exemple 640 colonnes × 480 lignes = 307 200 pixels.

Chaque pixel contient une **couleur**, codée par trois nombres entre 0 et 255 : la quantité de **rouge**, de **vert** et de **bleu** (RGB). `(0, 0, 0)` est noir, `(255, 255, 255)` est blanc, `(255, 0, 0)` est rouge pur.

Une image couleur est donc un tableau à **trois dimensions** : hauteur × largeur × 3 canaux.

```
            largeur (x) →
          ┌────┬────┬────┬────┐
hauteur   │ px │ px │ px │ px │     chaque px = [B, G, R]  (3 entiers 0-255)
  (y)     ├────┼────┼────┼────┤
  ↓       │ px │ px │ px │ px │
          └────┴────┴────┴────┘
```

### 2.2 Le voir en Python

Dans ce projet, la ligne `ok, frame = cap.read()` (fichier `posture/detector.py`) renvoie une image sous forme d'un tableau **NumPy** :

```python
import cv2
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
print(type(frame))     # <class 'numpy.ndarray'>
print(frame.shape)     # (480, 640, 3)  → hauteur, largeur, canaux
print(frame.dtype)     # uint8          → entiers de 0 à 255
print(frame[240, 320]) # [112  87  64]  → couleur du pixel central, en B, G, R
```

Trois conventions à mémoriser, car elles sont la source des bugs de débutant :

1. **L'axe y pointe vers le bas.** Le pixel `(0, 0)` est en haut à gauche. « Les épaules descendent » se traduit donc par « la coordonnée y des épaules **augmente** ». Vous retrouverez ce point dans `core.py`.
2. **NumPy indexe en `[ligne, colonne]`**, c'est-à-dire `[y, x]`, alors qu'en géométrie on écrit `(x, y)`. `frame.shape` donne `(hauteur, largeur, 3)`.
3. **OpenCV range les canaux en BGR, pas RGB.** Raison historique. La plupart des autres bibliothèques (MediaPipe, Pillow, matplotlib, PyTorch) attendent du RGB. D'où la conversion `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)` dans le projet.

### 2.3 Une vidéo

Une vidéo n'est rien d'autre qu'une suite d'images (des **frames**) affichées rapidement. Une webcam en fournit généralement 30 par seconde. Faire de la vision sur une vidéo, c'est faire de la vision sur chaque image, puis **raisonner sur la suite** (c'est ce que fait la machine à états du projet, voir 7.8).

### 2.4 Coordonnées en pixels et coordonnées normalisées

Une position dans l'image peut s'exprimer :

- en **pixels** : `(320, 240)` = colonne 320, ligne 240 ;
- en **coordonnées normalisées** : `(0.5, 0.5)` = « au milieu en largeur, au milieu en hauteur », indépendamment de la résolution.

MediaPipe renvoie des coordonnées normalisées (entre 0 et 1). Avantage : le même code fonctionne en 640×480 et en 1920×1080. Pour dessiner, on remultiplie : `x_px = int(x * largeur)`.

---

## 3. Les grandes familles de problèmes

Avant de choisir un outil, il faut savoir **nommer son problème**. Voici la carte du territoire.

| Tâche | Question posée | Sortie | Exemple d'outil |
|-------|----------------|--------|-----------------|
| **Classification** | Que contient cette image ? | Une étiquette (« chat ») | ResNet, EfficientNet |
| **Détection d'objets** | Où sont les objets et lesquels ? | Des boîtes + étiquettes | YOLO, Faster R-CNN |
| **Segmentation** | À quel objet appartient chaque pixel ? | Un masque par pixel | U-Net, Mask R-CNN, SAM |
| **Estimation de pose** (*keypoint detection*) | Où sont les articulations du corps ? | Des points `(x, y)` nommés | **MediaPipe Pose**, OpenPose, YOLO-pose |
| **Suivi** (*tracking*) | Est-ce le même objet que dans l'image d'avant ? | Un identifiant stable | ByteTrack, DeepSORT |
| **OCR** | Qu'est-il écrit ? | Du texte | Tesseract, PaddleOCR |
| **Reconnaissance faciale** | Qui est-ce ? | Une identité | ArcFace, FaceNet |
| **Estimation de profondeur** | À quelle distance est chaque pixel ? | Une carte de distances | MiDaS, Depth Anything |
| **Flux optique** | Dans quelle direction bouge chaque pixel ? | Un vecteur par pixel | Farnebäck, RAFT |

**Ce projet est un problème d'estimation de pose** suivi d'une **analyse géométrique** maison. C'est un schéma très fréquent dans l'industrie : un modèle générique fournit des primitives (points, boîtes, masques), et la valeur ajoutée du projet est dans la **logique métier construite par-dessus**.

Vous n'avez pas eu à entraîner un réseau de neurones pour ce projet. C'est le cas de la majorité des projets de vision aujourd'hui : on **réutilise un modèle pré-entraîné** et on écrit le raisonnement autour.

---

## 4. Deux époques : vision « classique » et deep learning

### 4.1 La vision classique (années 1970-2012)

On écrivait **à la main** les règles pour repérer ce qu'on cherchait, à base de mathématiques sur les pixels :

- **Filtres** : flou gaussien (réduire le bruit), seuillage (noir/blanc), morphologie (nettoyer des formes).
- **Contours** : le filtre de Canny détecte les endroits où la couleur change brutalement.
- **Points d'intérêt** : SIFT, ORB repèrent des « coins » reconnaissables d'une image à l'autre.
- **Cascades de Haar** : la première détection de visages en temps réel (2001), basée sur des contrastes clair/sombre (les yeux sont plus sombres que les joues, etc.).
- **Transformée de Hough** : trouver des lignes et des cercles.

Avantages : rapide, explicable, aucune donnée d'entraînement. Inconvénient : fragile. Un changement d'éclairage, d'angle ou de fond casse les règles. Détecter une épaule de face, de trois-quarts, en pull sombre ou en chemise claire avec des règles manuelles est quasi impossible.

OpenCV est né à cette époque et reste la bibliothèque de référence pour ces opérations. Dans ce projet, on l'utilise pour la capture, le miroir, la conversion de couleurs, le dessin et l'encodage JPEG.

### 4.2 Le deep learning (2012 à aujourd'hui)

En 2012, un réseau de neurones convolutif (AlexNet) écrase la compétition ImageNet. Depuis, l'approche dominante est : **on ne décrit plus les règles, on montre des exemples**.

Un **réseau de neurones convolutif** (CNN) est une suite de couches qui apprennent elles-mêmes les filtres utiles :

```
image → [filtres simples : bords, textures]
      → [combinaisons : yeux, coins de bouche, épaule]
      → [concepts : visage, torse, posture]
      → sortie (étiquette, coordonnées…)
```

Les premières couches ressemblent aux filtres de Canny ; les suivantes assemblent ces motifs en formes de plus en plus abstraites. Les poids de ces filtres sont trouvés automatiquement en montrant au réseau des **dizaines de milliers d'images annotées** (pour la pose : des photos de personnes où un humain a cliqué sur chaque articulation).

Avantages : robuste aux variations d'éclairage, d'angle, de vêtements. Inconvénients : demande des données, du calcul, et le résultat est difficile à expliquer.

### 4.3 Ce que ça change pour vous

En pratique, un projet moderne combine les deux :

- Un **modèle appris** (ici MediaPipe Pose) pour la partie « perception » difficile : trouver les articulations.
- De la **géométrie et des règles explicites** (ici `core.py`) pour la partie « raisonnement » : qu'est-ce qu'une mauvaise posture ?

Cette répartition est un choix d'ingénierie à comprendre. On aurait pu entraîner un classificateur « bonne / mauvaise posture » directement sur des images. Mais il aurait fallu des milliers d'images annotées, le résultat aurait dépendu de la personne, de la chaise, de la caméra, et on n'aurait pas pu expliquer à l'utilisateur **pourquoi** il est alerté. Avec la géométrie, la règle est lisible (« vos épaules sont descendues de 3 % de leur largeur ») et réglable.

---

## 5. Le pipeline universel d'un projet de vision

Quel que soit le projet, on retrouve toujours la même chaîne :

```
 ┌──────────────┐   ┌───────────────┐   ┌─────────┐   ┌──────────────────┐   ┌──────────┐   ┌───────────┐
 │ 1. Acquérir  │ → │ 2. Prétraiter │ → │ 3. Modèle│ → │ 4. Post-traiter  │ → │ 5. Décider│ → │ 6. Agir   │
 │ webcam, fichier│ │ redimensionner,│  │ CNN,    │   │ filtrer, lisser, │   │ seuils,  │   │ afficher, │
 │ flux réseau  │   │ couleurs,     │   │ règles  │   │ calculer des     │   │ machine  │   │ alerter,  │
 │              │   │ recadrer      │   │         │   │ grandeurs        │   │ à états  │   │ enregistrer│
 └──────────────┘   └───────────────┘   └─────────┘   └──────────────────┘   └──────────┘   └───────────┘
```

Dans ce dépôt, chaque étape a une place précise :

| Étape | Dans le projet | Fichier |
|-------|----------------|---------|
| 1. Acquérir | `cv2.VideoCapture(0)`, `cap.read()` | `posture/detector.py` |
| 2. Prétraiter | `cv2.flip`, `cv2.cvtColor(BGR2RGB)` | `posture/detector.py` |
| 3. Modèle | `pose.process(...)` (MediaPipe) | `posture/detector.py` |
| 4. Post-traiter | `extract_metrics`, `compute_metrics` | `posture/core.py` |
| 5. Décider | `deviations`, seuils, `update_status` | `posture/core.py`, `posture/detector.py` |
| 6. Agir | halo, pastille, icône, interface web | `posture/overlay.py`, `tray.py`, `server.py` |

Remarquez la séparation : **le modèle ne fait qu'une petite partie du travail**. Débutant, on imagine que « faire de la vision » = « appeler un modèle ». En réalité, l'essentiel du temps d'ingénierie va dans les étapes 2, 4, 5 et 6.

---

## 6. La boîte à outils

### 6.1 Les bibliothèques utilisées ici

| Outil | Rôle | Ce qu'il faut savoir |
|-------|------|----------------------|
| **NumPy** | Tableaux numériques | Une image *est* un `ndarray`. Toute opération « sur les pixels » est une opération NumPy. |
| **OpenCV** (`cv2`) | Couteau suisse de l'image | Capture, lecture/écriture de fichiers, conversions, filtres, dessin, encodage. Écrit en C++, très rapide. Convention BGR. |
| **MediaPipe** | Modèles pré-entraînés prêts à l'emploi (pose, mains, visage…) | Développé par Google, optimisé pour tourner sur CPU en temps réel. Version épinglée à `0.10.21` car l'API `mp.solutions` a été retirée ensuite. |
| **Pillow** | Images côté « application » | Utilisé ici pour dessiner l'icône de la barre des tâches. |

### 6.2 Les autres outils qu'il faut connaître

| Outil | Quand | Pourquoi |
|-------|-------|----------|
| **PyTorch** / **TensorFlow** | Entraîner ou affiner un modèle | Les deux frameworks de deep learning de référence. PyTorch domine la recherche et de plus en plus l'industrie. |
| **Ultralytics YOLO** | Détection, segmentation, pose en une ligne | `YOLO("yolov8n-pose.pt")(frame)`. Alternative moderne à MediaPipe, plus lourde, plus flexible, entraînable sur vos données. |
| **Hugging Face Transformers** | Modèles de vision récents (ViT, DETR, SAM, Depth Anything) | Téléchargement et inférence standardisés. |
| **scikit-image** | Traitement d'image scientifique | Plus « propre » qu'OpenCV pour des algorithmes classiques, moins rapide. |
| **ONNX Runtime** / **OpenVINO** / **TensorRT** | Déploiement | Exécuter un modèle entraîné vite et partout (CPU, GPU, embarqué). |
| **Label Studio**, **CVAT**, **Roboflow** | Annotation | Cliquer sur des milliers d'images pour créer un jeu de données. |
| **Matplotlib** | Visualisation | Afficher une image, une carte de chaleur, un histogramme de pixels. |

### 6.3 Le matériel

- **CPU** : suffit pour MediaPipe et les petits modèles (ce projet tourne sur n'importe quel portable).
- **GPU** (NVIDIA + CUDA) : indispensable pour entraîner, très utile pour les gros modèles en temps réel.
- **Embarqué** (Raspberry Pi, Jetson, téléphone) : contraintes fortes, modèles « lite » quantifiés.

---

## 7. Le projet, étape par étape

Chaque sous-section suit le même plan : **le concept général**, puis **comment c'est fait dans le code**, puis **pourquoi ce choix**.

### 7.1 Capturer la webcam

**Concept.** Une caméra est un périphérique qui livre des images en continu. Le système d'exploitation l'expose via une API (DirectShow / Media Foundation sous Windows, V4L2 sous Linux). OpenCV abstrait tout cela.

**Dans le code** (`posture/detector.py`) :

```python
cap = cv2.VideoCapture(0)             # 0 = première caméra du système
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # garder une seule image en attente
ok, frame = cap.read()                # ok=False si la caméra est absente ou prise
```

**Pourquoi.**

- `BUFFERSIZE = 1` : le pilote met les images dans une file. Si votre traitement est plus lent que la caméra, vous traitez des images **en retard** de plusieurs secondes. Avec un tampon de 1, on travaille toujours sur la dernière image. Piège classique du temps réel.
- `ok` est testé à chaque image : la webcam peut être débranchée ou prise par Teams. Le projet relâche alors la caméra (`cap.release()`) et réessaie toutes les 2 s. Un pipeline de vision doit supposer que **la source va tomber**.
- Le mode « Pause » libère aussi la caméra : une seule application à la fois peut l'utiliser sous Windows.

### 7.2 Préparer l'image (miroir, BGR → RGB)

**Concept.** Le **prétraitement** adapte l'image brute à ce que le modèle attend et à ce que l'utilisateur veut voir. Opérations courantes : redimensionnement, recadrage, conversion de couleurs, normalisation des valeurs (0-255 → 0-1), rotation.

**Dans le code** :

```python
frame = cv2.flip(frame, 1)                                   # 1 = miroir horizontal
results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
```

**Pourquoi.**

- Le **miroir** est purement ergonomique : quand vous bougez à droite, votre image bouge à droite, comme dans une glace. Sans cela, l'aperçu est déroutant.
- **BGR → RGB** : MediaPipe a été entraîné sur des images RGB. Si on lui donne du BGR, le rouge et le bleu sont inversés. Le modèle fonctionnera souvent quand même (la forme d'un corps ne dépend pas tant de la couleur), mais moins bien. Règle : **toujours donner au modèle le format exact sur lequel il a été entraîné**.
- Remarque : le miroir est appliqué **avant** le modèle. Cela inverse la gauche et la droite du point de vue de MediaPipe (son « épaule gauche » est en fait votre épaule droite). Le projet s'en protège en ne calculant que des **milieux et des valeurs absolues** (voir 7.5). C'est un bon exemple de la règle : « tout prétraitement a des conséquences en aval ».

### 7.3 Le modèle : MediaPipe Pose

**Concept.** Un modèle d'estimation de pose prend une image et renvoie la position de **points clés** (*keypoints* ou *landmarks*) du corps : nez, yeux, épaules, coudes, poignets, hanches, genoux, chevilles…

MediaPipe Pose utilise le modèle **BlazePose**, conçu par Google pour tourner en temps réel sur téléphone. Il renvoie **33 points**.

```
            0 nez
      2 œil g.   5 œil d.
    7 oreille g.   8 oreille d.
   ─────────────────────────────
  11 épaule g.        12 épaule d.
  13 coude g.         14 coude d.
  15 poignet g.       16 poignet d.
  23 hanche g.        24 hanche d.
  25 genou g.         26 genou d.
  27 cheville g.      28 cheville d.
  (+ doigts, talons, orteils)
```

Chaque point a quatre valeurs :

| Champ | Signification |
|-------|---------------|
| `x`, `y` | Position normalisée dans l'image (0 à 1), origine en haut à gauche |
| `z` | Profondeur estimée, relative aux hanches (peu fiable, non utilisée ici) |
| `visibility` | Probabilité (0 à 1) que le point soit visible et non caché |

**Comment ça marche à l'intérieur** (sans entrer dans les mathématiques) :

1. Un premier petit réseau, le **détecteur**, cherche une personne dans l'image entière et renvoie une boîte autour du torse.
2. Un second réseau, le **modèle de landmarks**, ne regarde que cette boîte (recadrée, redressée) et prédit les 33 points. Travailler sur une zone recadrée est beaucoup plus précis que sur l'image entière.
3. En vidéo, le détecteur n'est **pas relancé à chaque image** : on réutilise la boîte de l'image précédente, légèrement agrandie autour des points trouvés. C'est le **suivi** (*tracking*). Le détecteur n'est relancé que si la confiance chute.

**Dans le code** :

```python
with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
    ...
    results = pose.process(image_rgb)
    landmarks = results.pose_landmarks          # None si personne détectée
    point = landmarks.landmark[11]              # épaule gauche : point.x, .y, .z, .visibility
```

**Pourquoi.**

- `min_detection_confidence=0.5` : en dessous, on considère qu'il n'y a personne. `min_tracking_confidence=0.5` : en dessous, on relance le détecteur complet. Monter ces valeurs réduit les fausses détections mais augmente les « pertes ».
- `with ... as pose` : le modèle charge des fichiers et alloue de la mémoire ; le bloc `with` garantit la libération.
- Le modèle est créé **une seule fois** en dehors de la boucle. Le recréer à chaque image serait catastrophique (chargement de plusieurs dizaines de Mo).

### 7.4 Choisir les bons repères

**Concept.** Avoir 33 points ne veut pas dire les utiliser tous. Choisir les **bonnes caractéristiques** (*features*) est la décision la plus importante d'un projet. Les critères :

- Elles doivent **varier avec ce qu'on veut mesurer** (sensibilité).
- Elles ne doivent **pas varier avec ce qu'on ne veut pas mesurer** (robustesse).
- Elles doivent être **visibles** dans les conditions réelles d'usage.

**Dans le code** (`posture/core.py`) :

```python
LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER = 7, 8, 11, 12
```

**Pourquoi.**

- Les **épaules** sont toujours visibles de face, stables, et descendent quand on s'avachit.
- Les **oreilles** sont des points fixes du crâne : elles bougent avec la tête mais pas avec l'expression ni le regard.
- Le **nez** (point 0) a été testé et rejeté : il bouge dès qu'on regarde le clavier ou qu'on tourne la tête. Il est sensible à ce qu'on ne veut pas mesurer.
- Les **hanches** (23, 24) auraient été utiles (un vrai angle de dos), mais elles sont cachées par le bureau dans 100 % des cas d'usage réels.

Le réglage de ces choix s'est fait **en se filmant** et en regardant les valeurs. Il n'y a pas de formule : c'est de l'observation.

### 7.5 Transformer des points en mesures (géométrie)

**Concept.** Un modèle donne des coordonnées brutes. Il faut les transformer en **grandeurs qui ont un sens** pour la décision. Ici, les outils sont ceux de la géométrie du collège : milieux, distances, rapports, angles.

Deux problèmes classiques à résoudre :

1. **L'échelle** : si vous reculez de 20 cm, tous les points se rapprochent dans l'image. Une distance en pixels n'a aucun sens absolu.
2. **La symétrie** : gauche et droite peuvent être inversées (miroir) ou asymétriques (une épaule plus haute).

**Dans le code** :

```python
def compute_metrics(l_ear, r_ear, l_sh, r_sh):
    shoulder_y = (l_sh[1] + r_sh[1]) / 2           # hauteur moyenne des épaules
    ear_y = (l_ear[1] + r_ear[1]) / 2              # hauteur moyenne des oreilles
    width = abs(l_sh[0] - r_sh[0])                 # largeur d'épaules
    return shoulder_y, (shoulder_y - ear_y) / width, width
```

Trois nombres en sortent :

| Mesure | Formule | Ce qu'elle capte |
|--------|---------|------------------|
| `shoulder_y` | moyenne des y des deux épaules | Hauteur des épaules dans l'image (↑ quand on s'avachit, car y pointe vers le bas) |
| `head_ratio` | (épaules − oreilles) / largeur | Longueur apparente du cou, **en unités de largeur d'épaules** |
| `width` | \|x épaule g − x épaule d\| | Largeur d'épaules : sert d'**étalon** |

**Pourquoi.**

- **La normalisation par la largeur d'épaules** est l'idée clé. Votre largeur d'épaules ne change pas. Si elle apparaît deux fois plus grande, c'est que vous êtes deux fois plus près. En divisant tout par elle, les mesures deviennent **indépendantes de la distance à la caméra**. C'est le même principe qu'utiliser une pièce de monnaie comme échelle sur une photo.
- **Milieux et valeur absolue** : `(g + d) / 2` et `|g − d|` donnent le même résultat si on échange g et d. Les métriques sont donc **invariantes au miroir** et au fait que MediaPipe inverse gauche/droite. Le test `test_mirror_gives_same_metrics` le vérifie.
- **« Tête en avant » mesuré en vertical** : intuitivement, on voudrait mesurer l'avancée horizontale de la tête. Mais la caméra est de face : un mouvement vers la caméra n'est pas visible en x ou y, seulement en taille apparente (et en `z`, peu fiable). Ce qui se voit de face, c'est que **la tête descend** quand le cou se penche en avant : la distance oreilles-épaules se réduit. On mesure donc l'effet visible, pas la cause. Savoir **ce qu'une caméra peut et ne peut pas voir** est une compétence centrale.

### 7.6 La calibration : apprendre « votre » bonne posture

**Concept.** Il n'existe pas de « bonne posture » universelle en pixels : tout dépend de votre morphologie, de la hauteur de la caméra, de la chaise. Plutôt que de coder des valeurs absolues, on mesure **une référence personnelle** et on raisonne en **écart à cette référence**. C'est la **calibration**, présente dans presque tous les systèmes de mesure (balances, capteurs, caméras industrielles).

**Dans le code** (`posture/detector.py`, fonction `update_status`) :

```python
if state.calib_start is not None:
    if metrics:
        state.calib_samples.append(metrics)        # on accumule pendant 3 s
    remaining = CALIBRATION_SECONDS - (now - state.calib_start)
    if remaining > 0:
        return None                                # compte à rebours en cours
    reference = [sum(m[i] for m in samples) / len(samples) for i in range(3)]  # moyenne
```

**Pourquoi.**

- **Une moyenne sur 3 secondes** (environ 30 images) plutôt qu'une seule image : les coordonnées fournies par un modèle **tremblent** d'une image à l'autre de quelques millièmes, même immobile. C'est le **bruit**. Moyenner divise ce bruit. Règle générale : ne jamais faire confiance à une seule mesure.
- La référence est **persistée** dans un fichier JSON : trois nombres, pas d'image. Bon pour la vie privée, et la calibration survit au redémarrage.
- `valid_reference` vérifie que la référence est exploitable (largeur non nulle, tête au-dessus des épaules). **Valider les données avant de s'en servir**, surtout quand elles viennent d'un fichier qui a pu être modifié.

### 7.7 Décider : seuils et écarts

**Concept.** Une fois qu'on a une mesure et une référence, décider revient à comparer un **écart** à un **seuil**. Tout l'art est dans le choix de l'écart (quelle formule) et du seuil (quelle valeur).

**Dans le code** (`posture/core.py`) :

```python
def deviations(current, reference):
    shoulder_y, head_ratio, _ = current
    ref_shoulder_y, ref_head_ratio, ref_width = reference
    return (shoulder_y - ref_shoulder_y) / ref_width,   # avachissement
           1 - head_ratio / ref_head_ratio              # tête en avant

slouch = slouch_dev > 0.03    # épaules descendues de plus de 3 % de leur largeur
head   = head_dev   > 0.05    # cou raccourci de plus de 5 %
```

Lisez les deux écarts en français :

- **Avachissement** = « de combien de largeurs d'épaules mes épaules sont-elles descendues ? ». Si vos épaules font 40 cm, un seuil de 0,03 correspond à une descente d'environ 1,2 cm. C'est fin, mais le délai de 2 s (section suivante) évite les faux positifs.
- **Tête en avant** = « de quel pourcentage mon cou apparent s'est-il raccourci ? ». `1 − actuel/référence` donne 0 quand rien n'a changé, 0,05 quand il a perdu 5 %.

**Pourquoi.**

- Les écarts sont **sans unité** (des rapports). Ils signifient la même chose pour une personne grande ou petite, proche ou loin. Un seuil absolu en pixels n'aurait aucun sens.
- Les seuils ont été trouvés **empiriquement** : on se tient bien, on se tient mal, on regarde les jauges dans l'interface, on choisit une valeur qui sépare les deux. L'interface affiche ces écarts en direct précisément pour que l'utilisateur puisse refaire ce réglage chez lui. **Rendre les mesures visibles** est la meilleure façon de régler un système de vision.
- Le test `test_slouch_only` illustre une propriété importante : si les épaules **et** les oreilles descendent ensemble, le ratio tête/épaules ne change pas. Seul l'avachissement est détecté. Les deux mesures sont **indépendantes** : c'est voulu.

### 7.8 Filtrer dans le temps

**Concept.** Une décision prise image par image est instable : on se penche une seconde pour ramasser un stylo, on tousse, le modèle tremble. En vidéo, on dispose d'une arme supplémentaire : **le temps**. Techniques courantes :

- **Délai de confirmation** : n'alerter que si la condition dure N secondes.
- **Hystérésis** : seuil d'entrée différent du seuil de sortie, pour éviter de clignoter autour du seuil.
- **Lissage** : moyenne glissante ou filtre exponentiel sur les mesures.
- **Machine à états** : formaliser les situations possibles et les transitions.

**Dans le code**, c'est une machine à états avec un délai de confirmation :

```
   pas de référence ──► UNCALIBRATED
   repères invisibles ─► ABSENT  (analyse suspendue, pas d'alerte)

                  écart > seuil                 depuis ≥ 2 s
        ┌─────┐ ───────────────► ┌─────┐ ─────────────────────► ┌───────┐
        │ OK  │                  │ BAD │                         │ ALERT │
        └─────┘ ◄─────────────── └─────┘ ◄─────────────────────  └───────┘
                  écart ≤ seuil (à tout moment : retour immédiat à OK)
```

```python
if not (slouch or head):
    bad_since = None                 # posture correcte : on oublie tout
elif bad_since is None:
    bad_since = now                  # début d'une mauvaise posture
state = "ok" if bad_since is None else "alert" if now >= bad_since + alert_delay else "bad"
```

**Pourquoi.**

- Le délai de 2 s **filtre les mouvements brefs** sans rien coûter en précision : une vraie mauvaise posture dure des minutes.
- Le retour à OK est **immédiat** : dès que l'utilisateur se redresse, l'alerte disparaît. L'asymétrie (lent à alerter, rapide à pardonner) est un choix d'ergonomie.
- Le temps est passé en **paramètre** (`now`) plutôt que lu dans la fonction. Cela rend la machine à états **testable** sans attendre réellement 2 secondes (voir `test_alert_only_after_delay_then_clears`).

### 7.9 Gérer les cas où ça ne marche pas

**Concept.** Un système de vision **échoue en permanence** de façon normale : personne dans le champ, personne de dos, trop sombre, main devant le visage. Un bon système sait **dire « je ne sais pas »** plutôt que de deviner.

**Dans le code** (`posture/core.py`) :

```python
def extract_metrics(landmarks):
    pts = [landmarks[i] for i in (LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER)]
    if any(p.visibility < MIN_VISIBILITY for p in pts):
        return None                                  # un repère caché : on ne mesure pas
    metrics = compute_metrics(*[(p.x, p.y) for p in pts])
    return metrics if metrics[2] > 0.01 else None    # épaules confondues = de profil
```

**Pourquoi.**

- La `visibility` est une **mesure d'incertitude** fournie par le modèle. L'utiliser est indispensable : un point caché a quand même des coordonnées `x, y`, mais elles sont inventées.
- `width > 0.01` : si les deux épaules sont au même x, la personne est de profil. Diviser par une largeur quasi nulle donnerait des écarts gigantesques. Toujours se demander : « et si mon dénominateur vaut zéro ? ».
- `None` remonte jusqu'à la machine à états qui passe en `ABSENT` sans alerter. **Pas de donnée ≠ mauvaise donnée.**

### 7.10 Le budget CPU

**Concept.** Un pipeline de vision est coûteux. Chaque image passée dans un réseau de neurones représente des millions d'opérations. Pour une application qui tourne **toute la journée**, la consommation compte (batterie, ventilateur, autres applications).

**Dans le code** :

```python
FRAME_PERIOD = 0.1   # 10 images/s
...
time.sleep(max(0.0, FRAME_PERIOD - (time.time() - started)))
```

Et : l'image n'est encodée en JPEG que si l'interface web est ouverte (`if state.viewers`).

**Pourquoi.**

- La posture change en secondes, pas en millisecondes. **10 images/s** suffisent largement et divisent le coût par 3 par rapport aux 30 images/s natives. Première question d'un ingénieur vision : « de quelle fréquence ai-je vraiment besoin ? ».
- Ne calculer que ce qui est consommé (l'aperçu) est un réflexe général.
- Les leviers classiques pour réduire le coût, par ordre d'efficacité : baisser la fréquence, baisser la résolution, utiliser un modèle plus petit (`model_complexity=0` dans MediaPipe), ne traiter qu'une région d'intérêt, utiliser le GPU.

### 7.11 Afficher : squelette, JPEG, flux vidéo

**Concept.** Visualiser ce que « voit » le système est indispensable, pour le développeur (déboguer) comme pour l'utilisateur (comprendre, régler).

**Dans le code** :

```python
mp_drawing.draw_landmarks(frame, landmarks, mp_pose.POSE_CONNECTIONS)   # squelette sur l'image
state.jpeg = cv2.imencode(".jpg", frame)[1].tobytes()                    # compression JPEG
```

Puis, côté serveur (`posture/server.py`), les JPEG successifs sont envoyés au navigateur en **MJPEG** (`multipart/x-mixed-replace`) : une suite d'images JPEG dans une même réponse HTTP, que la balise `<img>` du navigateur sait afficher comme une vidéo. Aucun plugin, aucune bibliothèque côté client.

**Pourquoi.**

- `draw_landmarks` dessine **sur l'image BGR d'origine**, pas sur la copie RGB donnée au modèle. On garde une image « modèle » et une image « affichage ».
- Le **JPEG** divise la taille par 10 à 20 (une image 640×480 brute pèse 900 Ko, un JPEG 30-60 Ko).
- La version script `posture_assistant.py` utilise `cv2.imshow` et `cv2.waitKey` : c'est l'affichage de développement. `waitKey(1)` est obligatoire : c'est lui qui laisse OpenCV rafraîchir la fenêtre et lire le clavier.
- Les polices `cv2.FONT_HERSHEY_*` ne gèrent que l'ASCII : pas d'accents dans les textes dessinés par OpenCV (d'où « Epaules affaissees » dans le script).

### 7.12 Tester de la vision sans webcam

**Concept.** On ne peut pas lancer une webcam dans une intégration continue. La solution est **architecturale** : isoler la logique dans des fonctions pures qui prennent des nombres et renvoient des nombres.

**Dans le code** : `core.py` n'importe ni OpenCV ni MediaPipe. Les tests fabriquent des points à la main :

```python
REF = compute_metrics((0.45, 0.30), (0.55, 0.30), (0.35, 0.50), (0.65, 0.50))
# oreilles à y=0.30, épaules à y=0.50, largeur d'épaules 0.30

current = compute_metrics((0.45, 0.36), (0.55, 0.36), (0.35, 0.56), (0.65, 0.56))
# tout descendu de 0.06 = 20 % de la largeur d'épaules → avachissement
assert evaluate_posture(current, REF) == (True, False)
```

**Pourquoi.** C'est la leçon d'ingénierie la plus transférable de ce projet : **la partie vision (lente, non déterministe, dépendante du matériel) doit être une couche fine**, et tout le raisonnement doit être testable sans elle. Quand vous construirez un projet de vision, demandez-vous dès le début : « quelle partie de mon code pourrais-je tester avec quatre tuples écrits à la main ? ».

Pour tester le modèle lui-même, on utilise des **images ou vidéos enregistrées** (`cv2.VideoCapture("video.mp4")` fonctionne exactement comme une webcam), avec des résultats attendus annotés.

---

## 8. Le savoir-faire : les réflexes d'un ingénieur vision

Les connaissances s'apprennent dans les livres. Le savoir-faire s'acquiert sur des projets. Voici les réflexes que ce projet illustre et que vous retrouverez partout.

**1. Regarder ses données avant de coder.**
Avant d'écrire `compute_metrics`, il a fallu se filmer, afficher les 33 points, bouger, et observer lesquels varient avec la posture. Sans cette étape, on aurait utilisé le nez.

**2. Choisir des mesures invariantes.**
Toute mesure doit être indépendante de ce qu'on ne contrôle pas : distance (normaliser par une taille connue), position (travailler en relatif), miroir et asymétries (milieux, valeurs absolues), résolution (coordonnées normalisées).

**3. Calibrer plutôt que coder des constantes.**
Toute valeur absolue (« une épaule à y = 0,5 ») est fausse pour quelqu'un d'autre. Mesurer une référence, raisonner en écart.

**4. Moyenner, filtrer, attendre.**
Une mesure unique est bruitée. Moyenner dans l'espace (plusieurs points), dans le temps (plusieurs images), confirmer avant d'agir.

**5. Traiter l'incertitude comme une donnée.**
`visibility`, scores de confiance, `ok` de `cap.read()` : tout modèle et tout capteur fournit des indices de fiabilité. Les ignorer est la première cause de systèmes qui « marchent en démo et pas en vrai ».

**6. Rendre les mesures visibles.**
Jauges en direct, squelette dessiné, journal. On ne règle pas un seuil à l'aveugle.

**7. Séparer perception et décision.**
Le modèle fournit des primitives. La logique métier est à part, lisible, testable. Si demain MediaPipe est remplacé par YOLO-pose, seul `extract_metrics` change.

**8. Compter le coût.**
Fréquence, résolution, taille du modèle : choisir le minimum qui fait le travail.

**9. Prévoir l'échec.**
Caméra absente, personne hors champ, de profil, fichier corrompu : chaque cas a un état nommé et une réaction définie.

**10. Protéger la vie privée.**
Une caméra est un capteur intrusif. Ne garder que les nombres nécessaires, ne rien envoyer, le dire clairement. Ce n'est pas un détail juridique : c'est une condition pour que les gens acceptent d'utiliser votre système.

---

## 9. Limites et pièges de ce projet (et de la vision en général)

Comprendre ce qu'un système **ne sait pas faire** fait partie de le comprendre.

| Limite | Cause | Généralisation |
|--------|-------|----------------|
| Ne marche que de face | Les mesures reposent sur la projection frontale ; de profil, la largeur d'épaules s'effondre | Une caméra 2D ne voit qu'une projection. Changer d'angle change toute la géométrie. |
| Ne voit pas l'avancée réelle de la tête, seulement sa descente apparente | Le mouvement vers la caméra n'apparaît ni en x ni en y | La profondeur est perdue en 2D. La retrouver demande une seconde caméra (stéréo), un capteur de profondeur, ou un modèle qui l'estime (imprécis). |
| Sensible à la position de la caméra | Déplacer l'écran change la référence | Toute calibration est liée à une configuration. Recalibrer dès que la scène change. |
| Un pull à capuche, des cheveux longs, un casque audio peuvent cacher les oreilles | `visibility` baisse → `ABSENT` | Les occlusions sont le problème numéro un en vision. Le système préfère se taire plutôt que deviner. |
| Éclairage très faible ou contre-jour | Le modèle perd les repères | Les modèles sont robustes jusqu'à un certain point ; en dessous, aucun code ne compense une image noire. |
| Une personne qui passe derrière vous | MediaPipe ne suit qu'**une** personne ; il peut sauter sur l'autre | Les modèles mono-personne sont plus rapides mais fragiles en environnement partagé. |
| Le modèle a été entraîné sur des données qu'on ne contrôle pas | Précision potentiellement différente selon les morphologies, les vêtements, les carnations | **Biais des jeux de données** : un sujet sérieux. Toujours tester sur une population variée. |
| Seuils fixés sur une seule personne | Validés en usage réel… par l'auteur | Un réglage empirique sur un échantillon de 1 n'est pas une validation. Les jauges permettent à chacun de refaire le réglage. |

---

## 10. Expériences à faire vous-même

Le meilleur moyen de comprendre est de **modifier le code et observer**. Les expériences sont classées par difficulté. Faites-les dans un script à part (pas dans le paquet `posture/`), avec l'environnement virtuel du projet.

### Niveau 1 : toucher les pixels

```python
import cv2
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
cap.release()

print(frame.shape, frame.dtype)
print("Pixel central (B, G, R) :", frame[frame.shape[0] // 2, frame.shape[1] // 2])

gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)      # 1 canal au lieu de 3
edges = cv2.Canny(gray, 100, 200)                   # contours (vision classique)
frame[:, :, 2] = 0                                  # supprimer le canal rouge

cv2.imshow("gris", gray); cv2.imshow("contours", edges); cv2.imshow("sans rouge", frame)
cv2.waitKey(0)
```

Questions : pourquoi `gray.shape` n'a-t-il que deux dimensions ? Que se passe-t-il si vous passez `frame` (BGR) à `imshow` après avoir fait `cvtColor(BGR2RGB)` dessus ?

### Niveau 2 : voir ce que voit le modèle

```python
import cv2, mediapipe as mp
mp_pose = mp.solutions.pose
cap = cv2.VideoCapture(0)
with mp_pose.Pose() as pose:
    while True:
        ok, frame = cap.read()
        if not ok: break
        res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if res.pose_landmarks:
            h, w = frame.shape[:2]
            for i, lm in enumerate(res.pose_landmarks.landmark):
                color = (0, 255, 0) if lm.visibility > 0.5 else (0, 0, 255)
                cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, color, -1)
                cv2.putText(frame, str(i), (int(lm.x * w) + 5, int(lm.y * h)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        cv2.imshow("landmarks", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"): break
cap.release(); cv2.destroyAllWindows()
```

Observations à faire : cachez une main derrière le dos, quels points passent en rouge ? Tournez-vous de profil, que devient la largeur d'épaules ? Regardez le clavier : le nez (0) bouge-t-il plus que les oreilles (7, 8) ?

### Niveau 3 : mesurer le bruit

Restez immobile 5 secondes et imprimez `compute_metrics(...)` à chaque image. De combien les valeurs varient-elles ? Comparez à `SLOUCH_THRESHOLD = 0.03`. Tracez la courbe avec matplotlib. Puis appliquez une moyenne glissante sur 5 images et comparez.

### Niveau 4 : ajouter une mesure

Ajoutez la détection d'une **tête penchée sur le côté** : l'angle de la ligne oreille gauche → oreille droite par rapport à l'horizontale.

```python
import math
angle = math.degrees(math.atan2(r_ear[1] - l_ear[1], r_ear[0] - l_ear[0]))
```

Questions à vous poser, dans l'ordre du projet : cette mesure est-elle invariante à la distance ? au miroir (attention au signe) ? Faut-il une calibration ? Quel seuil ? Quel délai ? Écrivez le test unitaire **avant** de brancher la webcam.

### Niveau 5 : changer de modèle

Remplacez MediaPipe par `ultralytics` (`pip install ultralytics`) et le modèle `yolov8n-pose.pt` (17 points au format COCO : oreilles = 3 et 4, épaules = 5 et 6). Seul `extract_metrics` devrait changer. Comparez la vitesse (images/s) et la stabilité des points. Que se passe-t-il avec deux personnes dans le champ ?

### Niveau 6 : rejouer une vidéo

Enregistrez-vous 30 s avec `cv2.VideoWriter`, en vous tenant bien puis mal. Remplacez `VideoCapture(0)` par `VideoCapture("ma_video.mp4")`. Vous avez maintenant un **jeu de test reproductible** : vous pouvez changer les seuils et comparer objectivement les résultats. C'est ainsi qu'on travaille en équipe.

---

## 11. Pour aller plus loin

### Concepts à étudier ensuite, dans cet ordre

1. **Convolution et filtres** : comprendre ce que fait un noyau 3×3 sur une image (flou, contours). C'est la brique de base des CNN.
2. **Réseaux de neurones convolutifs** : couches de convolution, pooling, fonction d'activation. Le cours CS231n de Stanford est la référence.
3. **Transfer learning** : réutiliser un réseau pré-entraîné sur ImageNet et ne réentraîner que la fin pour votre problème. C'est ainsi qu'on fait 90 % des projets de classification avec peu de données.
4. **Détection d'objets** : la famille YOLO, la notion de boîte englobante, l'IoU, la *non-maximum suppression*.
5. **Métriques d'évaluation** : précision, rappel, matrice de confusion, mAP. Sans métrique, impossible de savoir si une modification améliore ou dégrade.
6. **Jeux de données** : COCO (détection, pose), ImageNet (classification). Comprendre comment ils sont annotés et leurs biais.
7. **Géométrie de la caméra** : modèle sténopé, calibration intrinsèque (distorsion de l'objectif), stéréovision. Indispensable dès qu'on veut mesurer des distances réelles.
8. **Transformers pour la vision** (ViT, DETR, SAM) : l'architecture qui remplace progressivement les CNN sur les gros modèles.

### Ressources

- **Cours** : CS231n (Stanford, gratuit en ligne), fast.ai *Practical Deep Learning*.
- **Livres** : *Computer Vision: Algorithms and Applications* (Szeliski, gratuit en PDF), *Deep Learning for Vision Systems* (Elgendy).
- **Documentation** : tutoriels OpenCV (docs.opencv.org), MediaPipe Solutions, Ultralytics.
- **Pratique** : Kaggle (compétitions et jeux de données), Roboflow Universe (jeux de données annotés).

### Projets pour progresser après celui-ci

| Projet | Ce qu'il apprend en plus |
|--------|--------------------------|
| Compteur de pompes / squats avec MediaPipe | Angles entre trois points, machine à états à plusieurs phases |
| Détection de somnolence (yeux fermés) avec MediaPipe Face Mesh | 468 points du visage, rapport d'aspect de l'œil |
| Lecteur de plaques d'immatriculation | Détection + OCR, enchaînement de deux modèles |
| Classificateur de déchets avec transfer learning | Entraîner un modèle, constituer et annoter un jeu de données, mesurer |
| Mesure d'objets avec une référence (pièce de monnaie) | Calibration d'échelle, contours, vision classique |
| Suivi de plusieurs personnes avec YOLO + ByteTrack | Tracking multi-objets, identifiants persistants |

---

## 12. Glossaire

| Terme | Définition |
|-------|------------|
| **BGR / RGB** | Ordre des canaux de couleur. OpenCV utilise BGR, presque tout le reste utilise RGB. |
| **Bruit** | Variations aléatoires d'une mesure d'une image à l'autre, même quand rien ne bouge. |
| **Calibration** | Mesure d'une référence dans les conditions réelles, pour raisonner ensuite en écart. |
| **CNN** (*Convolutional Neural Network*) | Réseau de neurones spécialisé pour les images, basé sur des filtres appris. |
| **Confiance** (*confidence*) | Score entre 0 et 1 qu'un modèle associe à sa prédiction. |
| **Détection** | Trouver où sont les objets (boîtes). |
| **Feature** (caractéristique) | Grandeur calculée à partir de l'image et utilisée pour décider. |
| **Frame** | Une image d'une vidéo. |
| **FPS** (*frames per second*) | Nombre d'images traitées par seconde. |
| **Hystérésis** | Utiliser deux seuils (entrée, sortie) pour éviter les oscillations autour d'un seuil unique. |
| **Inférence** | Utiliser un modèle entraîné pour faire une prédiction (par opposition à l'entraînement). |
| **Invariance** | Propriété d'une mesure qui ne change pas quand quelque chose de non pertinent change (distance, miroir…). |
| **Keypoint / Landmark** | Point caractéristique nommé (épaule, œil…) localisé par un modèle. |
| **Machine à états** | Modèle de programme où le système est à tout instant dans un état nommé, avec des transitions définies. |
| **MJPEG** | Flux vidéo constitué d'une suite d'images JPEG indépendantes. |
| **Modèle pré-entraîné** | Réseau déjà entraîné par d'autres, qu'on réutilise tel quel ou qu'on affine. |
| **Normalisation** | Diviser une mesure par une grandeur de référence pour la rendre sans unité et comparable. |
| **Occlusion** | Un objet en cache un autre. |
| **Pipeline** | Chaîne d'étapes de traitement, de l'acquisition à l'action. |
| **Pixel** | Plus petit élément d'une image, porteur d'une couleur. |
| **Pose estimation** | Tâche consistant à localiser les articulations d'un corps. |
| **Prétraitement** | Transformations appliquées à l'image avant le modèle. |
| **ROI** (*Region Of Interest*) | Sous-partie de l'image sur laquelle on concentre le traitement. |
| **Segmentation** | Attribuer une classe à chaque pixel. |
| **Seuil** | Valeur au-delà de laquelle on change de décision. |
| **Temps réel** | Traitement assez rapide pour suivre le flux de la source sans prendre de retard. |
| **Tracking** | Suivre un objet d'une image à l'autre au lieu de le redétecter à chaque fois. |
| **Transfer learning** | Réutiliser un modèle entraîné sur une tâche pour en apprendre une autre avec peu de données. |
| **Visibility** | Dans MediaPipe, probabilité qu'un point soit visible et non caché. |

---

## En une page : comment marche ce projet

Si vous ne deviez retenir qu'un paragraphe :

> Dix fois par seconde, la webcam fournit une grille de 640×480 pixels en BGR. On la retourne en miroir et on la convertit en RGB. Un réseau de neurones pré-entraîné (MediaPipe Pose) y localise 33 points du corps, en coordonnées normalisées, avec un score de visibilité. On n'en garde que quatre : les oreilles et les épaules. Si l'un d'eux est caché, on ne mesure rien. Sinon, on calcule trois nombres : la hauteur moyenne des épaules, la longueur apparente du cou, et la largeur d'épaules qui sert d'étalon pour rendre le tout indépendant de la distance. Lors de la calibration, on moyenne ces nombres pendant trois secondes pour obtenir la référence personnelle de l'utilisateur. Ensuite, à chaque image, on calcule l'écart à cette référence : si les épaules sont descendues de plus de 3 % de leur largeur, ou si le cou s'est raccourci de plus de 5 %, la posture est mauvaise. Si elle le reste deux secondes, on alerte. Dès qu'elle redevient bonne, on oublie tout. Toute cette logique tient dans des fonctions pures qui manipulent des nombres, testées sans caméra ; la vision proprement dite n'en est qu'une couche fine et remplaçable.

C'est cela, la computer vision appliquée : un modèle qui transforme des pixels en points, et de l'ingénierie soigneuse qui transforme des points en décisions fiables.
