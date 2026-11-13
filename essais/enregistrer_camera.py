"""Essai « ordinateur deplace » (critere CA7), protocole n° 2 : le buste reste immobile, l'ordinateur bouge
LENTEMENT pendant l'enregistrement. Seuls les 33 reperes MediaPipe sont ecrits (des nombres, aucune image).

Usage (assistant arrete) : .venv\\Scripts\\python essais\\enregistrer_camera.py essais\\donnees\\AAAA-MM-JJ-camera
Puis : .venv\\Scripts\\python essais\\analyser_camera.py essais\\donnees\\AAAA-MM-JJ-camera\\camera.jsonl
"""
import json
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp

# (code, consigne pendant l'enregistrement) ; le code « reference » sert de calibration, « avache » attend une alerte
STEPS = [
    ("reference", "Restez DROIT et immobile, ne touchez a rien"),
    ("incline_arriere", "Buste immobile : inclinez LENTEMENT l'ecran vers l'ARRIERE (~10 deg)"),
    ("incline_avant", "Buste immobile : inclinez LENTEMENT l'ecran vers l'AVANT (~20 deg)"),
    ("tourne", "Buste immobile : TOURNEZ lentement l'ordinateur (~10 deg)"),
    ("deplace", "Buste immobile : faites GLISSER lentement l'ordinateur (~10 cm)"),
    ("avache", "Lachez l'ordinateur et AVACHISSEZ-vous"),
]
PREP, RECORD = 4, 12
WIN = "Essai ordinateur deplace"


def text(img, s, y, color):
    cv2.putText(img, s, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
    cv2.putText(img, s, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(0)
    cv2.namedWindow(WIN)
    cv2.setWindowProperty(WIN, cv2.WND_PROP_TOPMOST, 1)
    with mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose, \
            open(out / "camera.jsonl", "w") as f:
        deadline, started = time.time() + 600, False
        while not started and time.time() < deadline:
            ok, frame = cap.read()
            if ok:
                frame = cv2.flip(frame, 1)
                text(frame, "Cliquez ici puis ESPACE pour commencer", 40, (0, 255, 255))
                text(frame, "Gardez le BUSTE IMMOBILE, seul l'ordinateur bouge", 75, (255, 255, 255))
                cv2.imshow(WIN, frame)
            started = cv2.waitKey(30) & 0xFF == ord(" ")
        if not started:
            sys.exit("Essai non demarre (pas d'appui sur ESPACE)")

        for step, instruction in STEPS:
            t0 = time.time()
            while time.time() - t0 < PREP + RECORD:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)
                t = time.time() - t0 - PREP
                res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                if t >= 0 and res.pose_landmarks:
                    f.write(json.dumps({"etape": step, "t": round(t, 2), "lm": [
                        [round(p.x, 4), round(p.y, 4), round(p.z, 4), round(p.visibility, 3)]
                        for p in res.pose_landmarks.landmark]}) + "\n")
                color = (0, 200, 255) if t < 0 else (0, 255, 0)
                label = (f"Prochaine etape dans {-t:.0f} s : posez la main sur l'ecran, buste droit" if t < 0
                         else f"Pendant {RECORD - t:.0f} s")
                text(frame, instruction, 40, color)
                text(frame, label, 75, color)
                cv2.imshow(WIN, frame)
                cv2.waitKey(1)
    cap.release()
    cv2.destroyAllWindows()
    print(f"Enregistre : {out / 'camera.jsonl'}")


if __name__ == "__main__":
    main()
