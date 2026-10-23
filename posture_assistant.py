"""
Assistant de posture, version script (fenetre OpenCV, sans arriere-plan).
L'application complete est le paquet `posture` : python -m posture.

Utilisation : python posture_assistant.py
Touches : ESPACE = calibrer / recalibrer, Q ou ECHAP = quitter.
"""

import sys
import time

import cv2
import mediapipe as mp

from posture.core import ALERT_DELAY_SECONDS, evaluate_posture, extract_metrics

CALIBRATION_SECONDS = 3.0   # duree du compte a rebours / moyenne de la calibration
GREEN, RED, ORANGE, WHITE = (0, 200, 0), (0, 0, 255), (0, 165, 255), (255, 255, 255)

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


# --- Affichage ------------------------------------------------------------
def draw_banner(frame, text, color):
    """Bandeau colore en haut de l'image avec un message (Hershey = ASCII, donc pas d'accents)."""
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 60), color, -1)
    cv2.putText(frame, text, (15, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, WHITE, 2, cv2.LINE_AA)


# --- Boucle principale ----------------------------------------------------
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        sys.exit("Erreur : impossible d'ouvrir la webcam (deja utilisee ou absente ?).")

    reference = None            # metriques de la bonne posture
    calib_start = None          # instant de debut de calibration, None si pas en cours
    calib_samples = []
    bad_since = None            # debut de la mauvaise posture en cours

    try:
        with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
            while True:
                ok, frame = cap.read()
                if not ok:
                    print("Erreur : flux webcam interrompu.")
                    break

                frame = cv2.flip(frame, 1)  # effet miroir
                results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

                metrics = None
                if results.pose_landmarks:
                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                    metrics = extract_metrics(results.pose_landmarks.landmark)

                now = time.time()

                if calib_start is not None:
                    # Calibration : moyenne des mesures pendant le compte a rebours
                    if metrics:
                        calib_samples.append(metrics)
                    remaining = CALIBRATION_SECONDS - (now - calib_start)
                    if remaining > 0:
                        draw_banner(frame, f"Calibration en cours... {remaining:.0f}s", ORANGE)
                    elif calib_samples:
                        reference = tuple(sum(m[i] for m in calib_samples) / len(calib_samples) for i in range(3))
                        calib_start, bad_since = None, None
                    else:
                        calib_start = None  # personne non vue pendant le compte a rebours : on revient a l'invite

                elif reference is None:
                    draw_banner(frame, "Tenez-vous droit et appuyez sur ESPACE", ORANGE)

                elif metrics is None:
                    # Utilisateur hors champ : on suspend l'analyse sans declencher d'alerte
                    bad_since = None
                    draw_banner(frame, "Utilisateur hors champ", ORANGE)

                else:
                    slouching, head_forward = evaluate_posture(metrics, reference)
                    if slouching or head_forward:
                        bad_since = bad_since or now
                    else:
                        bad_since = None

                    if bad_since and now - bad_since > ALERT_DELAY_SECONDS:
                        draw_banner(frame, "Attention, redressez-vous !", RED)
                        cv2.rectangle(frame, (0, 0), (frame.shape[1] - 1, frame.shape[0] - 1), RED, 12)
                        reasons = [r for r, on in (("Epaules affaissees", slouching),
                                                   ("Tete en avant", head_forward)) if on]
                        cv2.putText(frame, " / ".join(reasons), (15, frame.shape[0] - 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, RED, 2, cv2.LINE_AA)
                    else:
                        draw_banner(frame, "Posture OK", GREEN)

                cv2.imshow("Assistant de posture", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord(" "):
                    calib_start, calib_samples = now, []
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
