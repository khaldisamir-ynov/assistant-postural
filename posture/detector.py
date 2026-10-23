"""Detection en continu par la webcam : met a jour state.status (et l'apercu si l'interface l'affiche)."""

import logging
import time

import cv2
import mediapipe as mp

from posture import core
from posture.state import state, update_settings

log = logging.getLogger(__name__)

CALIBRATION_SECONDS = 3.0
FRAME_PERIOD = 0.1  # 10 images/s suffisent pour la posture et menagent le CPU sur une journee

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


def run():
    """Relance la detection apres une erreur inattendue plutot que de s'arreter en silence."""
    while state.running:
        try:
            _loop()
        except Exception:
            log.exception("Erreur de detection, redemarrage dans 5 s")
            state.status, state.jpeg = {"state": "error"}, None
            time.sleep(5)


def _loop():
    cap, bad_since = None, None
    try:
        with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
            while state.running:
                s = state.settings
                if not s["enabled"]:
                    if cap:
                        cap.release()  # libere la webcam (visio, etc.)
                        cap = None
                        log.info("Pause : webcam liberee")
                    state.jpeg, state.calib_start, bad_since = None, None, None
                    state.status = {"state": "paused"}
                    time.sleep(0.5)
                    continue

                if cap is None:
                    cap = cv2.VideoCapture(0)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # evite de traiter des images en retard
                started = time.time()
                ok, frame = cap.read()
                if not ok:
                    # Webcam absente ou prise par une autre application : on reessaie plus tard
                    if state.status.get("state") != "camera_error":
                        log.warning("Webcam indisponible, nouvel essai toutes les 2 s")
                    cap.release()
                    cap = None
                    state.jpeg, state.status = None, {"state": "camera_error"}
                    time.sleep(2)
                    continue

                frame = cv2.flip(frame, 1)  # effet miroir pour l'apercu
                results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                landmarks = results.pose_landmarks
                metrics = core.extract_metrics(landmarks.landmark) if landmarks else None
                if state.viewers:  # apercu seulement si l'interface le regarde
                    if landmarks:
                        mp_drawing.draw_landmarks(frame, landmarks, mp_pose.POSE_CONNECTIONS)
                    state.jpeg = cv2.imencode(".jpg", frame)[1].tobytes()
                else:
                    state.jpeg = None

                bad_since = update_status(metrics, s, bad_since, time.time())
                time.sleep(max(0.0, FRAME_PERIOD - (time.time() - started)))
    finally:
        if cap:
            cap.release()


def update_status(metrics, s, bad_since, now):
    """Machine a etats calibration / posture. Retourne le debut de la mauvaise posture en cours (ou None)."""
    if state.calib_start is not None:
        if metrics:
            state.calib_samples.append(metrics)
        remaining = CALIBRATION_SECONDS - (now - state.calib_start)
        if remaining > 0:
            state.status = {"state": "calibrating", "remaining": remaining}
            return None
        samples, state.calib_start = state.calib_samples, None
        reference = [sum(m[i] for m in samples) / len(samples) for i in range(3)] if samples else None
        if core.valid_reference(reference):
            update_settings({"reference": reference})
            log.info("Calibration enregistree")
        else:
            log.warning("Calibration ratee : aucune personne detectee pendant le compte a rebours")
        return None

    if s["reference"] is None:
        state.status = {"state": "uncalibrated"}
        return None
    if metrics is None:
        state.status = {"state": "absent"}  # hors champ : pas d'alerte
        return None

    slouch_dev, head_dev = core.deviations(metrics, s["reference"])
    slouch = s["detect_slouch"] and slouch_dev > s["slouch_threshold"]
    head = s["detect_head"] and head_dev > s["head_threshold"]
    if not (slouch or head):
        bad_since = None
    elif bad_since is None:
        bad_since = now
    alert_since = bad_since + s["alert_delay"] if bad_since is not None else None
    state.status = {
        "state": "ok" if bad_since is None else "alert" if now >= alert_since else "bad",
        "slouch": slouch, "head": head, "slouch_dev": slouch_dev, "head_dev": head_dev, "alert_since": alert_since,
    }
    return bad_since
