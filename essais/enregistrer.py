"""Essai guide : enregistre les 33 reperes MediaPipe (des nombres, aucune image) pendant une serie de postures.

Usage (depuis la racine du projet, assistant arrete pour liberer la webcam) :
    .venv\\Scripts\\python essais\\enregistrer.py essais\\donnees\\AAAA-MM-JJ [--etape N | --postures a,b] [--photos]
--etape N : seulement les postures des etapes 1 a N (etape 1 : droit, tete en avant, clavier, avachi, droit ;
etape 2 : + penche).
--postures a,b : seulement ces postures, pour en refaire une (ex. droit,avache : « droit » sert de calibration au banc).
--photos : enregistre AUSSI une photo toutes les 2 s dans photos/ (essai VLM, avec l'accord de la personne filmee).
Reperes du buste (C13) : poses au debut de la calibration de « droit », suivis image par image ; seules leurs
positions sont ecrites (champ « buste », en pixels, null = perdu ; « wh » = taille de l'image).
--gommettes vert|rose|bleu : 2 ou 3 gommettes de cette couleur collees sur le buste ; leurs centres sont ecrits a
chaque image (champ « gommettes »). L'ecran d'attente montre celles qui sont vues : verifier avant ESPACE.
Puis : .venv\\Scripts\\python essais\\rejouer.py essais\\donnees\\AAAA-MM-JJ\\landmarks.jsonl
  ou : .venv\\Scripts\\python essais\\comparer_vlm.py essais\\donnees\\AAAA-MM-JJ
"""
import json
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from reperes_buste import COLORS, follow, seed, stickers

# (code, consigne) : les codes sont ceux attendus par rejouer.py
POSTURES = [
    ("droit", "Asseyez-vous BIEN DROIT, face a l'ecran"),
    ("tete_avant", "Avancez la TETE vers l'ecran (dos immobile)"),
    ("clavier", "Regardez le CLAVIER (baissez juste les yeux / le menton)"),
    ("avache", "AVACHISSEZ-vous (epaules qui tombent)"),
    ("penche", "Penchez-vous sur le COTE / accoudez-vous"),
    ("menton_main", "MENTON dans la main, coude sur le bureau"),
    ("trop_pres", "Rapprochez tout le BUSTE de l'ecran"),
    # vrais objets : avec --photos, une main vide serait notee « telephone » sans rien de visible (essai VLM, C9)
    ("telephone", "VRAI TELEPHONE a l'oreille, tete comme d'habitude"),
    ("boire", "BUVEZ dans une VRAIE tasse"),
    ("droit2", "De nouveau BIEN DROIT"),
]
# Postures utiles a chaque etape (cumulatives) ; sans --etape, toutes les postures
BY_STEP = {1: {"droit", "tete_avant", "clavier", "avache", "droit2"}, 2: {"penche"}}
# Preparation de 6 s (et non 4) : essai du 2026-10-30, les images signalees au clavier etaient toutes dans la transition
# depuis la posture precedente (1,3 premiere seconde) ; le banc les comptait comme une erreur de detection
PREP, RECORD = 6, 12
PHOTO_PERIOD = 2  # 6 photos par posture
WIN = "Essai posture"


def text(img, s, y, color):
    cv2.putText(img, s, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
    cv2.putText(img, s, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    step = int(sys.argv[sys.argv.index("--etape") + 1]) if "--etape" in sys.argv else None
    wanted = set().union(*(BY_STEP[n] for n in BY_STEP if n <= step)) if step else {p[0] for p in POSTURES}
    if "--postures" in sys.argv:
        wanted = set(sys.argv[sys.argv.index("--postures") + 1].split(","))
    postures = [p for p in POSTURES if p[0] in wanted]
    photos = out / "photos" if "--photos" in sys.argv else None
    color = sys.argv[sys.argv.index("--gommettes") + 1] if "--gommettes" in sys.argv else None
    if color and color not in COLORS:
        sys.exit(f"Couleur inconnue : {color} (choix : {', '.join(COLORS)})")
    if photos:
        photos.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(0)
    cv2.namedWindow(WIN)
    cv2.setWindowProperty(WIN, cv2.WND_PROP_TOPMOST, 1)
    with mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose, \
            open(out / "landmarks.jsonl", "w") as f:
        deadline, started = time.time() + 600, False
        while not started and time.time() < deadline:
            ok, frame = cap.read()
            if ok:
                frame = cv2.flip(frame, 1)  # meme effet miroir que l'application
                if color:  # verifier que les gommettes sont vues avant de commencer
                    res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    dots = stickers(frame, res.pose_landmarks.landmark, color) if res.pose_landmarks else []
                    for x, y in dots:
                        cv2.circle(frame, (int(x), int(y)), 12, (0, 0, 255), 3)
                    text(frame, f"Gommettes vues : {len(dots)}", 120, (0, 255, 255))
                text(frame, "Cliquez ici puis ESPACE pour commencer", 40, (0, 255, 255))
                text(frame, f"{len(postures)} postures x {RECORD} s, suivez les consignes", 80, (255, 255, 255))
                cv2.imshow(WIN, frame)
            started = cv2.waitKey(30) & 0xFF == ord(" ")
        if not started:
            sys.exit("Essai non demarre (pas d'appui sur ESPACE)")

        bust, prev_gray = None, None
        for name, instruction in postures:
            t0, shots = time.time(), 0
            while time.time() - t0 < PREP + RECORD:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)
                el = time.time() - t0
                res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if bust is not None:
                    bust = follow(prev_gray, gray, bust)
                elif name == "droit" and el >= PREP + 4 and res.pose_landmarks:  # debut de la calibration du banc
                    bust = seed(gray, res.pose_landmarks.landmark)
                prev_gray = gray
                dots = stickers(frame, res.pose_landmarks.landmark, color) if color and res.pose_landmarks else []
                if el >= PREP and res.pose_landmarks:
                    f.write(json.dumps({"posture": name, "t": round(el - PREP, 2), "lm": [
                        [round(p.x, 4), round(p.y, 4), round(p.z, 4), round(p.visibility, 3)]
                        for p in res.pose_landmarks.landmark], "wh": [gray.shape[1], gray.shape[0]],
                        "buste": None if bust is None else [
                            None if np.isnan(x) else [round(float(x), 1), round(float(y), 1)] for x, y in bust],
                        **({"gommettes": [[round(x, 1), round(y, 1)] for x, y in dots]} if color else {})}) + "\n")
                if photos and el >= PREP + shots * PHOTO_PERIOD:
                    cv2.imwrite(str(photos / f"{name}_{shots}.jpg"), frame)  # avant que les consignes soient dessinees
                    shots += 1
                for x, y in dots:
                    cv2.circle(frame, (int(x), int(y)), 12, (0, 0, 255), 3)
                ink = (0, 200, 255) if el < PREP else (0, 255, 0)
                label = f"Preparez-vous : {PREP - el:.0f}" if el < PREP else f"Enregistrement : {PREP + RECORD - el:.0f} s"
                text(frame, instruction, 40, ink)
                text(frame, label, 80, ink)
                cv2.imshow(WIN, frame)
                cv2.waitKey(1)
    cap.release()
    cv2.destroyAllWindows()
    print(f"Enregistre : {out / 'landmarks.jsonl'}")


if __name__ == "__main__":
    main()
