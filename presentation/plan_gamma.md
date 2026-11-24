# Plan de présentation pour Gamma

Partie 1 : à coller dans Gamma (« Créer » → « Coller du texte »). Chaque `---` sépare deux cartes.
Partie 2 : notes pour l'oral, carte par carte. Chiffres et sources : `SPECIFICATIONS.md` § 6, `presentation/evaluation.ipynb`, `presentation/baseline.md`, `presentation/mesures/`.

---

# Partie 1 : cartes

# Assistant de posture

Repérer ses mauvaises postures au bureau, et s'en rendre compte sans être dérangé.

100 % local : aucune image ne quitte l'ordinateur.

Samir Khaldi · M2 Ynov · novembre 2026

---

# Le besoin

- Au bureau, on prend de mauvaises postures **sans s'en rendre compte**, et on les garde des heures.
- Un rappel doit être **discret** : pas de son, pas de fenêtre, jamais de vol du clavier.
- La webcam filme une personne chez elle ou au travail : **la vie privée n'est pas négociable**.
- Il doit tenir **toute la journée** sans ralentir l'ordinateur, et s'installer sans droits administrateur.

---

# La réponse : une application de bureau locale

- La webcam du portable, analysée par **MediaPipe Pose** sur le processeur, 10 images/s.
- Comparaison à **votre** posture de référence (calibration de 3 s).
- Signalement en escalade douce : **liseré ambre** en bord d'écran après 2 s, puis **pastille « Redressez-vous »** avec le motif après 30 s.
- Une page locale : état en direct, journée, rapport, réglages.
- Windows et Mac, icône près de l'horloge, lancement avec la session.

---

# Ce qui est détecté

- **Posture affaissée** : la hauteur haut de la tête → épaules raccourcit (seuil 3 %).
- **Penché sur le côté / accoudé** : l'axe du cou s'incline (seuil 6°).
- En option : tête en avant, trop près de l'écran, tête appuyée sur la main, buste affaissé.
- Toutes les mesures sont divisées par la largeur des épaules : elles ne dépendent pas de la distance à la caméra.
- Lissage sur 1 s, hystérésis, délai de 2 s : un mouvement bref ne déclenche rien.

---

# La démarche : mesurer avant de décider

- **Des critères écrits et datés avant chaque essai** (C1 à C16), jamais modifiés après avoir vu les résultats.
- **Un banc d'essai** : on enregistre les repères (jamais l'image), puis on les rejoue dans la vraie logique de l'application.
- **Une détection, un paramètre à la fois** : quand tout change en même temps, on ne sait plus ce qui marche.
- Chaque piste se termine par une **décision écrite** : gardée, en option ou écartée.

---

# Ce qui a été essayé, et écarté

| Piste | Résultat | Décision |
|---|---|---|
| Profondeur (Depth Anything V2) | Pas mieux que la 2D, 0,6 à 2,3 s par image | Écartée |
| Images puis vidéos générées | Le modèle déplace le corps plus que la posture | Écartées pour noter les postures |
| VLM / LLM à la place de MediaPipe | 65 à 79 % de fausses alertes, ou la moitié des postures ratées | Écartés |
| VLM téléphone / boisson | 16/16 sur images générées, 8/9 sur vraies photos | Écarté |
| Repères suivis sur le t-shirt | Les plis bougent, les points se perdent | Écartés |
| Détecteur « épaules » (3 mesures) | Signale le clavier | Retiré |
| Axe tête → bassin | Voit mieux l'avachi, mais signale le clavier | Option désactivée |

---

# Évaluation : le protocole

- **4 séances enregistrées à un bureau** (30 oct., puis 13 nov. A, B, C) : 6 836 images, 24 épisodes de 12 s.
- **Vérité terrain** : la consigne de l'enregistrement (droit, clavier, tête en avant, avachi, penché).
- **Prédiction** : la vraie logique de l'application, avec les réglages par défaut.
- **Aucun apprentissage** : un seul seuil réglé (3 %), sur la 1re séance, puis testé sur les 3 autres.
- On compte **par épisode** (ce que vit l'utilisateur), puis par image.

---

# Évaluation : ce que vit l'utilisateur

- **0 fausse alerte sur 12 épisodes de bonne posture** (droit, droit2, regard vers le clavier).
- **10 mauvaises postures sur 12 alertées** (rappel 83 %, intervalle 55 à 95 %).
- Les 2 ratées : **l'avachi**, dans les séances A et B.
- Par image : précision **94 %**, rappel **80 %**, F1 **0,86**, fausses alertes **5 %**.

---

# Pourquoi l'avachi est raté : la mesure, pas le seuil

- En faisant varier le seuil de 1 à 8 %, **aucune valeur** ne marche pour les séances A et B.
- Vu de face, s'avachir ne raccourcit la hauteur tête-épaules que de **1,6 à 1,8 %** : autant que le bruit d'une bonne posture.
- Ce qui a été essayé pour l'avachi : épaules, axe tête-bassin, bascule de la tête, repères du buste. Rien ne passe les critères sans signaler le clavier.
- Point faible **connu, mesuré et assumé**.

---

# Pourquoi MediaPipe, et pas un VLM

| | Mauvaises postures vues | Fausses alertes | Latence | Coût | Ce qui sort du poste |
|---|---|---|---|---|---|
| MediaPipe (photo par photo) | 72 % | 32 % | 0,06 s | 0 | rien |
| Meilleurs VLM / LLM | 92 à 97 % | 65 à 79 % | 0,5 à 5,2 s | 0,06 à 0,24 $/h | photo ou repères |
| VLM le plus sobre (gemma-4) | 39 à 47 % | 3 à 9 % | 1,1 à 3 s | 0,02 à 0,04 $/h | photo |

118 photos, 2 passes, intervalles de confiance à 95 %. Dans l'application, le lissage et le délai font tomber les fausses alertes de MediaPipe à **0 sur 12 épisodes**.

---

# Les autres exigences, mesurées

- **Performance (C3), mesurée sur 1 h d'usage réel** : **1,35 %** du processeur en moyenne (p95 1,6 %, pointe 3 %), **310 Mo** de mémoire. Budget : 5 % et 500 Mo. Inférence : 20 ms par image.
- **Vie privée (C7)** : audit du code, aucune image écrite ni envoyée. Seul appel réseau : le rapport par IA, sur demande, avec des chiffres agrégés.
- **Hors champ, pause, webcam occupée (C5)**, vérifiés en usage réel : 40 min d'absence sans aucune alerte et reprise seule au retour ; en pause, le processeur tombe à 0,15 % ; webcam prise par une autre application, puis reprise seule à sa libération.
- **Plusieurs écrans (C6)** : essayé en usage réel ; après l'ajout du 2e écran, 1 alerte d'1 s en 81 s, contre 3 en 32 s avant.
- **Fiabilité (C4)** : 76 tests automatiques, CI Windows et macOS.

---

# Première heure d'usage réel

- Journal de l'assistant, état noté **chaque seconde** pendant 1 h de travail.
- Après la calibration : en bonne posture **56 %** du temps, en alerte **30 %**.
- Environ **100 alertes par heure**, brèves (4 s en médiane). Réglages plus stricts que Normal.
- **Elles étaient justes** : j'étais penché ou accoudé à une table haute.
- **L'escalade protège de l'agacement** : sur environ 100 liserés de quelques secondes, **3 seulement** sont devenus une pastille.
- À valider ensuite : une journée entière au réglage Normal. Les niveaux Souple / Normal / Exigeant existent pour ajuster.

---

# Reproductibilité

- **La détection rejoue le même verdict** : l'évaluation relancée le 24 nov. donne des sorties **identiques** à celles du 20 nov.
- **Le logiciel se réinstalle et ses tests repassent** : `requirements.lock`, MediaPipe épinglé, CI à chaque push.
- **Livraison** : exe Windows et app Mac construits par GitHub Actions, attachés aux releases v0.2.0, v0.3.0, v1.0.0.
- **Historique git** : une branche par fonctionnalité, fusionnées dans `develop`, versions sur `main`.

---

# Le produit aujourd'hui

- **Journée** : % en bonne posture, temps de chaque mauvaise posture, déroulé par demi-heure, 7 derniers jours.
- **Rapport de la journée calculé sur l'ordinateur** : bilan, moments, 3 à 5 conseils selon vos chiffres. Une IA peut le rédiger, en option.
- **Prise en main** : guide du premier lancement avec l'image webcam, exigence Souple / Normal / Exigeant.
- **Lieux et écrans** : chaque lieu garde ses calibrations, jusqu'à 4 écrans.
- Interface **React + shadcn/ui**, compilée en un seul fichier, sans rien charger depuis Internet.

---

# Limites, dites franchement

- **Une seule personne, une webcam, 4 séances** : les intervalles restent larges.
- **L'avachi au bureau** est raté dans 2 séances sur 4.
- **Ordinateur sur les genoux** : hors périmètre (la webcam suit le buste).
- **Une journée réelle complète** (fréquence des alertes au réglage Normal) et **le Mac** restent à tester.
- **Écrans multiples** : un essai court en usage réel, sans journal de l'écran regardé.

---

# Et ensuite

- Enregistrer **d'autres personnes** (protocole prêt : `essais/dataset_video.md`).
- **L'avachi** : essai des gommettes de couleur sur le buste, préparé mais pas encore enregistré.
- **Webcam déplacée sans recalibrer** (F13) : compensation par le décor, à reprendre avec un 2e protocole.
- Tester l'app Mac sur un vrai Mac.

---

# Démo

1. État en direct et jauges.
2. Se tenir mal : le liseré, puis la pastille.
3. Hors champ, pause.
4. Changer de lieu depuis l'icône.
5. Rapport de la journée.

---

# Partie 2 : notes pour l'oral

- **Le besoin** : insister sur « sans s'en rendre compte » et « discret ». Tout le reste en découle : zéro fausse alerte compte plus que tout détecter.
- **La démarche** : c'est le cœur de la soutenance. Montrer une ligne de `SPECIFICATIONS.md` § 4 (critère daté avant l'essai) et une décision au § 6.3.
- **Épisodes avant images** : les images se suivent à 20 à 30 par seconde, elles ne sont pas indépendantes ; l'intervalle par image paraît trop sûr. L'utilisateur, lui, vit « une alerte ou pas ».
- **MediaPipe à 32 % de fausses alertes photo par photo** : ce n'est pas l'application. Elle lisse sur 1 s, attend 2 s et se calibre sur 3 s, d'où 0 fausse alerte par épisode.
- **Avachi** : ne pas s'en excuser. Montrer la courbe de sensibilité au seuil (notebook § 3) : aucun seuil ne sépare, donc c'est la mesure qui ne voit pas l'avachi, vue de face.
- **Reproductibilité** : la même évaluation, relancée quatre jours plus tard avec le code actuel, redonne les mêmes chiffres au caractère près.
- **Questions probables** : « Pourquoi pas de deep learning entraîné ? » Aucun jeu public ne couvre la posture au bureau vue par la webcam (notebook § 5) ; et sans données d'autres personnes, entraîner reviendrait à apprendre une seule personne.
