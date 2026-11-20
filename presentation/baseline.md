# Fiche de référence — performance

Méthode du notebook `diagnostiquer_performances.ipynb` (§ 12), appliquée au modèle du projet. ResNet-18 ne sert pas : l'assistant n'utilise pas de classifieur d'images. Le réseau mesuré est **MediaPipe Pose 0.10.21**, complexité 1 (la valeur par défaut de `posture/detector.py`) : `pose_detection.tflite` puis `pose_landmark_full.tflite`.

L'image est une **personne générée** (`essais/donnees/genere/photos/droit_0.jpg`, jeu C10), ramenée à 640×480. Ce n'est pas une personne filmée, donc C7 est respecté. Protocole du cours : 10 passages de chauffe, puis 50 mesures pour la latence (lot de 1) et 30 pour le débit. Pas de GPU CUDA : rien à synchroniser. Script : `presentation/mesurer_baseline.py`.

**Correction du 2026-11-20.** La première fiche utilisait des pixels aléatoires. Sur une telle image, MediaPipe ne trouve personne (`pose_landmarks` vaut `None`) : seul le **détecteur** tourne, jamais le réseau des repères. Ce n'est pas le chemin de l'application. Le script vérifie désormais qu'une personne est vue, et il mesure les deux chemins réels.

## Matériel et modèle

| | |
|--|--|
| Modèle | MediaPipe Pose 0.10.21, complexité 1, processeur |
| Poids des deux fichiers | 8,96 MiB |
| Machine | Intel64 Family 6 Model 170 Stepping 4, Python 3.12.7, Windows |
| Image | 640×480, trois canaux, comme une webcam qu'on ne redimensionne pas |
| Mémoire du processus | 206 Mo après les mesures, 302 Mo au pic (deux instances de MediaPipe chargées, Python inclus). L'application complète avait été mesurée à 307 Mo (critère C3) : ce n'est pas le même périmètre. |

## Latence d'une image

Inférence seule (`pose.process`), après chauffe.

| | Suivi (chemin de l'application) | Première image (détecteur + repères) | 1re fiche, pixels aléatoires (détecteur seul) |
|--|--|--|--|
| Médiane | **20,1 ms** | 38,3 ms | 28 à 41 ms selon la chaleur de la machine |
| Moyenne | 20,8 ms | 38,7 ms | 29 à 41 ms |
| P95 | 25,6 ms | 45,7 ms | 33 à 51 ms |
| P99 | 30,6 ms | 48,9 ms | 33 à 55 ms |

- **Suivi** : une fois la personne trouvée, MediaPipe ne relance pas le détecteur. Il applique le réseau des repères sur la zone de l'image précédente. C'est le coût de presque toutes les images d'une journée.
- **Première image** : quand la personne apparaît, ou après une perte, il faut le détecteur, puis les repères (`static_image_mode=True` force ce chemin à chaque appel).

Le besoin de l'assistant est de 10 images/s, donc 100 ms par image. Le suivi n'en utilise que 20 %. L'utilisateur, lui, attend 2 s de mauvaise posture avant le halo : la latence du réseau n'est pas le délai qu'il ressent.

Prétraitement (miroir, puis BGR vers RGB) : médiane de 0,10 ms. Post-traitement (`extract_metrics`, sur de vrais repères cette fois) : 0,006 ms. Ni l'un ni l'autre ne mérite une optimisation.

## Débit et taille de lot

Dans l'API utilisée par l'application, MediaPipe Pose n'accepte pas de lot d'images : un lot de N, c'est N images l'une après l'autre. En suivi, le débit reste d'environ **50 images/s** du lot 1 au lot 16, et le temps du lot suit le nombre d'images (20, 40, 82, 164, 320 ms).

En usage, le lot utile est 1 : une webcam, une personne. Grossir le lot allongerait l'attente sans traiter plus d'images par seconde.

## À retenir pour la soutenance

La référence à conserver : **une médiane d'environ 20 ms par image en suivi et 38 ms pour la première image sur ce processeur, un débit d'environ 50 images/s, des fichiers de modèle de 9 MiB et un pré-traitement négligeable.** L'ancienne fiche mesurait le détecteur seul, sur une image sans personne.

Une optimisation ne compte que si elle est remesurée avec ce même script, sur la même machine, après la même chauffe.

Chiffres bruts : `baseline_performance.csv` (une ligne par chemin) et `baseline_throughput.csv` (suivi).
