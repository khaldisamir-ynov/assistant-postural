# Spécifications, critères de réussite, essais et démo

Assistant de posture, version 0.4.0. Document de référence **avant toute nouvelle modification** : chaque amélioration doit dire quel critère elle vise, et se vérifier avec le protocole décrit ici.

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
- enregistrement d'images.

---

## 2. Exigences fonctionnelles

| ID | Exigence |
|----|----------|
| **F1** | Détecter 5 mauvaises postures par rapport à la posture de référence de l'utilisateur : **épaules affaissées**, **tête en avant**, **penché sur le côté / accoudé**, **trop près de l'écran**, **tête appuyée sur la main**. |
| F2 | Chaque détection peut être activée ou désactivée, et sa tolérance est réglable. |
| F3 | Un mouvement bref ne déclenche rien : la mauvaise posture doit durer (délai réglable, 2 s par défaut). Les mesures sont lissées sur ~1 s et le retour à « OK » exige de repasser sous 80 % du seuil (hystérésis). |
| **F4** | Signalement en escalade douce : liseré ambre pulsant en bord d'écran, puis après 30 s (réglable) une pastille « Redressez-vous » avec le motif. Les deux laissent passer les clics et ne prennent jamais le focus. |
| **F5** | Calibration de 3 s : la première seconde est ignorée, la référence est la médiane des mesures. Elle est **refusée si l'utilisateur bouge**, avec un message. Si les épaules sont trop bas dans l'image, un avertissement s'affiche. |
| **F6** | **Lieux de travail** nommés librement (10 au plus), choisis à la main dans la page ou dans le menu de l'icône. Chaque lieu garde ses propres calibrations. |
| **F7** | **Plusieurs écrans** : jusqu'à 4 références par lieu (« Ajouter un écran »). La posture est jugée par rapport à la référence la plus proche. |
| F8 | Hors champ (tête ou épaules invisibles) : aucune alerte. Webcam prise par une autre application : nouvel essai toutes les 2 s. **Pause** : la webcam est libérée. |
| F9 | **Statistiques du jour** : temps en bonne posture, temps suivi, nombre d'alertes, motif principal. Remises à zéro chaque jour. |
| F10 | **Coach IA** (facultatif) : un LLM Hugging Face propose 3 conseils à partir des statistiques du jour, avec le token de l'utilisateur. |
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
| Coach | Après quelques minutes suivies : « Demander un bilan au coach » | 3 conseils, ou un message clair si le token est absent ou invalide |
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
Cliquer dans la fenêtre, puis ESPACE. Pour chaque posture : 4 s de préparation (consigne en orange), puis 12 s d'enregistrement (en vert), avec une photo toutes les 2 s.

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

### 6.5 Jeu généré et VLM téléphone / boisson (C9, C10), 2026-11-06 — provisoire

**Provisoire** : images générées seulement, à confirmer sur de vraies photos (§ 4.4).

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
| 8 | Carte **Aujourd'hui** → **Demander un bilan au coach** | 3 conseils de Qwen (Hugging Face) | Seuls 8 chiffres sont envoyés au LLM |
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
| 1 | Regard vers le clavier : ne pas compter la descente des épaules quand seule la tête bouge, ou exiger que les épaules descendent sans que la tête baisse | C1 clavier |
| 2 | Dérive naturelle : référence qui suit lentement l'utilisateur quand il est droit, ou tolérance épaules adaptée au bruit mesuré pendant la calibration | C1 images |
| 3 | Essais réels des écrans multiples et revérification de C5 en 0.4.0 | C5, C6 |
| 4 | Téléphone et boisson : VLM sur la **photo**, avec accord explicite (l'image quitterait la machine), ou détection de mains avec MediaPipe Hands si elles sont dans le champ | Nouveau critère à définir |
| 5 | Essais sur d'autres personnes et d'autres webcams (les seuils actuels viennent d'une seule personne) | Validité de C1 et C2 |
