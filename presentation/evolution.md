# Évolution et reproductibilité

Pour la soutenance. Le détail chiffré de chaque essai reste dans `SUIVI_DEVELOPPEMENT.md`. Ici : les étapes globales, puis comment mesurer ce qu'un autre poste peut refaire.

Les métriques demandées par le professeur sont dans `presentation/evaluation.ipynb` : précision, rappel, F1 et fausses alertes, par image et par épisode, sur les 4 séances de bureau. **Par épisode** (ce que voit l'utilisateur) : 10 mauvaises postures alertées sur 12, aucune fausse alerte sur 12 bonnes postures. **Par image** : précision de 94 %, rappel de 80 %, F1 de 0,86. Les 2 épisodes ratés sont l'avachi.

## 1. Le modèle de détection

Une seule idée tient jusqu'au bout : MediaPipe Pose, en local, repères des oreilles et des épaules, mesures divisées par la largeur des épaules. Pas d'apprentissage des poids. Les « modèles » essayés ensuite sont des pistes écartées, ou un coach qui ne voit que des chiffres.

| Étape | Ce qui est mesuré | Décision |
|-------|-------------------|----------|
| 1. Géométrie 2D | Descente des épaules, tête qui se rapproche des épaules | Gardé. Base du MVP. |
| 2. Seuils sur une personne réelle (30 oct.) | Penché, trop près, main sur le menton, calibration | Seuils écrits (5 %, 0,10, 0,25, main à 2 écarts d'yeux). Première seconde de calibration ignorée, médiane, refus si la personne bouge. |
| 3. Profondeur | Depth Anything V2, en local | Écarté. Ne sépare pas mieux « tête en avant » et « regard clavier », et coûte 0,6 à 2,3 s par image. |
| 4. Une détection à la fois | Hauteur tête–épaules (seuil 3 %), puis angle du cou (seuil 6°) | Gardé. Chaque seuil est fixé avant l'essai de validation, rejoué par `essais/rejouer.py`. |
| 5. Images puis vidéos générées | Qwen-Image, FLUX, Wan, LTX : même personne, postures modifiées | Écarté pour les postures fines. Le modèle déplace le corps plus que la posture. Utile seulement pour des objets bien visibles, et encore : le jeu généré surestimait les VLM. |
| 6. VLM et LLM sur l'image | Silhouette, photo, repères | Écarté pour détecter. Trop de fausses alertes, ou l'objet (téléphone) est caché par la main. Envoyer l'image est refusé. |
| 7. Buste | Épaules qui descendent, flux optique sur le t-shirt, axe tête–hanches | Épaules retiré (échoue au bureau). Flux optique écarté (les plis bougent). Axe tête–hanches laissé en option, désactivé : les hanches sont hors champ, MediaPipe les invente. |
| 8. État actuel | MediaPipe seul pour alerter. Qwen, via Hugging Face, rédige le bilan du jour à partir des compteurs | Détection 100 % locale. Le coach est facultatif et ne reçoit aucune image. |

Le point faible assumé : l'avachi au bureau. Selon la séance, il est vu ou non. L'ordinateur sur les genoux est hors périmètre, parce que la webcam suit le buste.

## 2. Le logiciel

| Version | Ce que l'utilisateur obtient |
|---------|------------------------------|
| 23 oct. | Script webcam, puis POC : page locale et point ambre. |
| 0.2.0 | Paquet `posture/`, tests, icône, halo puis pastille, réglages, exe Windows, démarrage avec la session. |
| 0.3.0 | Même signalement sur Mac Apple Silicon, app construite par GitHub Actions. Pas encore tenue en main sur un Mac. |
| 0.4.0, publiée en 1.0.0 | Lissage sur ~1 s, hystérésis, statistiques du jour, lieux, plusieurs écrans, coach. |
| 13 nov. | Page en trois onglets (Aujourd'hui, Rapport IA, Réglages). Ancien script retiré : une seule voie, le paquet. |

## 3. Mesurer la reproductibilité

Trois questions, trois commandes. On note le résultat, on ne le résume pas en une note unique.

**Le logiciel se réinstalle et les tests repassent.** Autre poste, Python 3.9 à 3.12, dépôt cloné :

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.lock -e ".[dev]"
.\.venv\Scripts\python -m pytest
```

MediaPipe est épinglé à `0.10.21` (`requirements.lock`, `pyproject.toml`) : les versions suivantes ont retiré `mp.solutions`. Sur cette machine, le 20 nov. 2026, le venv déjà en place donne **66 tests passés, 1 ignoré**. L'ignoré est le LaunchAgent, réservé à macOS. Ce chiffre est celui d'un venv existant, pas d'une installation vierge.

**La détection rejoue le même verdict.** `essais/rejouer.py` ne tire pas au sort : deux passages sur le même `landmarks.jsonl` doivent afficher les mêmes pourcentages. C'est le critère de reproductibilité du modèle.

**Ce qu'un clone ne peut pas refaire.** `essais/donnees/` est dans `.gitignore`. Les pourcentages du suivi (avachi à 71 %, tête en avant à 90 %, etc.) ne se recalculent pas sans ces fichiers. Les images et vidéos générées non plus : elles dépendent d'un token Hugging Face, d'un modèle qui change, et elles ne sont pas rejouées à l'identique. Le coach non plus : la réponse du LLM varie, et elle n'entre pas dans la détection. L'application Mac est construite en CI, mais personne ne l'a encore lancée sur un Mac.

À dire en soutenance : le comportement du logiciel et le banc sont reproductibles ; les essais humains ne le sont que si l'on fournit les `landmarks.jsonl`. Les pistes génératives et le coach ne le sont pas, et elles ne portent pas la détection.

## 4. Infrastructure matérielle

Rien à côté de l'ordinateur. Pas de GPU, pas de caméra externe, pas de serveur. La détection tourne sur le processeur, avec la webcam déjà dans l'écran.

| Élément | Ce qui suffit |
|---------|----------------|
| Machine | Windows 10 ou 11, ou Mac à puce Apple (M1 et suivants, macOS 11 ou plus). Pas d'application prête pour un Mac Intel. |
| Webcam | Celle du portable, face à la personne. Tête et épaules dans le champ. |
| Calcul | MediaPipe sur le processeur, 10 images/s. Le budget fixé (C3) : au plus 5 % du processeur et 500 Mo. Mesure : 1,3 % de la machine (28 % d'un cœur sur 22), 307 Mo. |
| Réseau | Aucun pour détecter. Seulement si l'utilisateur demande le bilan du coach : des chiffres partent vers Hugging Face, jamais une image. |
| Installation | Un exe Windows ou un zip Mac, sans droits administrateur. Les réglages restent dans le dossier de l'utilisateur. |

L'aperçu webcam se replie : replié, aucune image n'est encodée. C'est ce qui garde le coût bas sur une journée. La compensation quand on déplace l'écran (F13) n'est pas dans le produit : l'essai n'a pas atteint ses critères.

## 5. Ce qui importe à l'usage

La détection ne vaut que si la personne oublie l'outil et reste à un bureau.

- **Le poste.** Bureau, webcam dans l'écran, personne de face. Sur les genoux ou dans un canapé, la caméra suit le buste : s'avachir ne change pas l'image (essai du 6 nov., avachi à 0 %). Les épaules trop basses dans l'image rendent MediaPipe instable : l'assistant prévient en dessous de 75 % de la hauteur.
- **La calibration.** Trois secondes droit et immobile. La première seconde est ignorée, la référence est une médiane, et elle est refusée si l'on bouge. Chaise, écran ou lieu différent : on recalibre. Un lieu mémorise jusqu'à quatre écrans, pour qu'un regard sur le côté ne soit pas une mauvaise posture.
- **Ne pas déranger.** Pas de son, pas de fenêtre, le halo et la pastille laissent passer la souris. Un mouvement bref ne compte pas : le halo attend 2 s, la pastille 30 s. Les mesures sont lissées sur environ 1 s.
- **La webcam est exclusive.** Pendant une visio, menu Pause : la caméra est rendue à Teams ou Zoom. Si une autre application la prend, l'assistant réessaie tout seul toutes les 2 s, sans alerte.
- **La journée entière n'est pas encore mesurée.** Le critère CPU est tenu sur 30 s. La gêne du halo, la fréquence des alertes et le processeur sur une vraie journée de travail restent à faire.
