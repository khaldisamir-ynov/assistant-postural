"""Detection en continu par la webcam : met a jour state.status (et l'apercu si l'interface l'affiche)."""

import logging
import statistics
import time
from collections import deque
from datetime import date

import cv2
import mediapipe as mp

from posture import core, stats
from posture.state import save_reference, state

log = logging.getLogger(__name__)

CALIBRATION_SECONDS = 3.0
FRAME_PERIOD = 0.1  # 10 images/s suffisent pour la posture et menagent le CPU sur une journee
SMOOTHING_FRAMES = 10  # moyenne sur ~1 s : le bruit de MediaPipe ne fait plus osciller l'etat
HYSTERESIS = 0.8  # en mauvaise posture, retour a OK seulement sous 80 % du seuil (pas de clignotement)
STATS_SAVE_PERIOD = 60
# Essai du 2026-10-30 : en restant immobile, la hauteur des epaules varie de moins de 1 % de leur largeur ;
# dans les secondes ou l'on se replace, de 10 a 15 %
CALIBRATION_MAX_MOVE = 0.03
EDGE_Y = 0.75  # epaules plus bas que 75 % de l'image : MediaPipe y est nettement moins stable

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
    recent = deque(maxlen=SMOOTHING_FRAMES)
    recent_hand = deque(maxlen=SMOOTHING_FRAMES)  # None si main invisible : une main sortie du champ ne reste pas « pres »
    last_tick = saved_at = time.time()
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
                recent_hand.append(core.hand_face_distance(landmarks.landmark) if landmarks else None)
                if metrics:
                    recent.append(metrics)
                else:
                    recent.clear()
                if state.viewers:  # apercu seulement si l'interface le regarde
                    if landmarks:
                        mp_drawing.draw_landmarks(frame, landmarks, mp_pose.POSE_CONNECTIONS)
                    state.jpeg = cv2.imencode(".jpg", frame)[1].tobytes()
                else:
                    state.jpeg = None

                now, prev_state = time.time(), state.status.get("state")
                smoothed = tuple(sum(v) / len(recent) for v in zip(*recent)) if recent else None
                seen = [d for d in recent_hand if d is not None]
                hand_dist = statistics.median(seen) if len(seen) * 2 >= len(recent_hand) else None
                bad_since = update_status(smoothed, s, bad_since, now, hand_dist)
                # dt borne : une pause ou une webcam perdue ne compte pas comme du temps suivi
                state.stats = stats.record(state.stats, prev_state, state.status, min(now - last_tick, 1.0),
                                           date.today().isoformat())
                last_tick = now
                if now - saved_at > STATS_SAVE_PERIOD:
                    stats.save(state.stats)
                    saved_at = now
                time.sleep(max(0.0, FRAME_PERIOD - (time.time() - started)))
    finally:
        stats.save(state.stats)
        if cap:
            cap.release()


def update_status(metrics, s, bad_since, now, hand_dist=None):
    """Machine a etats calibration / posture. Retourne le debut de la mauvaise posture en cours (ou None)."""
    if state.calib_start is not None:
        if metrics:
            state.calib_samples.append(metrics)
        remaining = CALIBRATION_SECONDS - (now - state.calib_start)
        if remaining > 0:
            state.status = {"state": "calibrating", "remaining": remaining}
            return None
        # 1re seconde ignoree (on lache la souris), mediane : robuste a une image aberrante
        samples, state.calib_start = state.calib_samples[len(state.calib_samples) // 3:], None
        reference = [statistics.median(m[i] for m in samples) for i in range(len(samples[0]))] if samples else None
        if not core.valid_reference(reference):
            message = "Calibration ratée : tête et épaules non visibles. Recommencez."
        elif statistics.pstdev(m[0] for m in samples) / reference[2] > CALIBRATION_MAX_MOVE:
            message = "Calibration refusée : vous avez bougé. Restez immobile 3 s et recommencez."
        else:
            save_reference(reference, state.calib_add)
            message = "Calibration enregistrée."
            if reference[0] > EDGE_Y:
                message += (" Vos épaules sont tout en bas de l'image : inclinez l'écran vers le bas ou reculez un peu"
                            " pour une mesure plus stable.")
        state.calib_message = {"text": message, "at": now}
        log.info(message)
        return None

    refs = s["places"][s["place"]]
    if s["detect_posture"]:
        refs = [r for r in refs if len(r) > 4]  # calibration d'avant l'etape 1 : sans hauteur tete-epaules
    if not refs:
        state.status = {"state": "uncalibrated"}
        return None
    if metrics is None:
        state.status = {"state": "absent"}  # hors champ : pas d'alerte
        return None

    # Plusieurs ecrans : on juge par rapport a la posture de reference la plus proche (ecarts dans les deux sens)
    # shortcut: proximite sur les seuls ecarts epaules/tete ; ajouter l'orientation (largeur d'epaules, nez)
    # si deux ecrans proches se confondent en usage reel
    def distance(ref):
        slouch_dev, head_dev, _, _, shortening = core.deviations(metrics, ref)
        return max(abs(slouch_dev) / s["slouch_threshold"], abs(head_dev) / s["head_threshold"],
                   abs(shortening) / s["posture_threshold"])
    screen = min(range(len(refs)), key=lambda i: distance(refs[i]))
    slouch_dev, head_dev, lean_dev, close_dev, posture_dev = core.deviations(metrics, refs[screen])
    margin = HYSTERESIS if bad_since is not None else 1.0
    posture = s["detect_posture"] and posture_dev > s["posture_threshold"] * margin
    close = s["detect_close"] and close_dev > s["close_threshold"] * margin
    # Trop pres : la perspective fausse les mesures epaules/tete, on ne signale que la distance
    slouch = not close and s["detect_slouch"] and slouch_dev > s["slouch_threshold"] * margin
    head = not close and s["detect_head"] and head_dev > s["head_threshold"] * margin
    lean = s["detect_lean"] and lean_dev > s["lean_angle"] * margin
    # Distance : plus petite = pire, donc la marge s'applique dans l'autre sens
    hand = s["detect_hand"] and hand_dist is not None and hand_dist < s["hand_threshold"] / margin
    if not (posture or slouch or head or lean or close or hand):
        bad_since = None
    elif bad_since is None:
        bad_since = now
    alert_since = bad_since + s["alert_delay"] if bad_since is not None else None
    state.status = {
        "state": "ok" if bad_since is None else "alert" if now >= alert_since else "bad",
        "posture": posture, "posture_dev": posture_dev,
        "slouch": slouch, "head": head, "lean": lean, "close": close, "hand": hand, "hand_dist": hand_dist,
        "slouch_dev": slouch_dev, "head_dev": head_dev,
        "lean_dev": lean_dev, "close_dev": close_dev, "alert_since": alert_since,
        "screen": screen,
    }
    return bad_since
