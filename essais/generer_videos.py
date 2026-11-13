"""Videos generees (criteres C14, SPECIFICATIONS.md § 4.9) : l'image « droit » d'une personne generee est animee
(image -> video, routeur HF). Meme cadrage que l'image de depart, mouvement continu : notable image par image.

Ecrit <dossier>/videos/<posture>_<n>.mp4 (deja presentes = non regenerees), puis mesure chaque video avec MediaPipe
par rapport a l'image de depart (calibration) et affiche les criteres C14.
Usage : .venv\\Scripts\\python essais\\generer_videos.py essais\\donnees\\genere [--personnes 1,3] [--modele m] [--fournisseur fal-ai|wavespeed]
Videos dans <dossier>/videos_<modele>/.
Configuration : HF_TOKEN et HF_BILL_TO dans .env. Payant.
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import mediapipe as mp
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from posture import core  # noqa: E402

MODEL = "Wan-AI/Wan2.2-I2V-A14B-Diffusers"
# Consignes v2 (2026-11-13, apres Wan2.2 et LTX-2) : camera, corps, geste separes, plus un prompt negatif
STILL = (" Camera: fixed webcam on the desk, no camera movement, no zoom, no pan, same framing and same room for the "
         "whole video.")
NEGATIVE = ("camera movement, zoom, pan, dolly, cut, new scene, different room, standing up, leaning back, "
            "head nodding, talking")
EXTRA = {"fal-ai": {"aspect_ratio": "16:9"}}  # fal-ai refuse le 4:3 (« aspect_ratio auto »)
CLIPS = {  # code de enregistrer.py (temoin : « droit2 ») -> mouvement demande
    "droit2": "The person stays perfectly still, sitting upright, looking at the camera; only the eyes blink.",
    # 1re version (« slumps... sinks lower ») : Wan2.2 a fait se renverser la personne en arriere, tete levee
    "avache": ("The person slowly hunches forward over the desk: the back rounds, the shoulders roll forward and "
               "down, the head drops a little, then the person stays hunched."),
    "tete_avant": ("The person slowly pushes only the head and neck forward toward the screen, like a turtle; the "
                   "shoulders and chest stay exactly in place; then the person holds the head forward."),
}
SEEN_MIN, OK_MIN = 0.9, 0.9  # C14a ; part des images qui doit respecter C14b / C14c
THIRD = (core.POSTURE_THRESHOLD / 3, core.LEAN_ANGLE / 3, core.CLOSE_THRESHOLD / 3)


def frames_metrics(path, pose):
    """Mesures MediaPipe de chaque image (None si tete ou epaules non vues) et images par seconde."""
    cap, out = cv2.VideoCapture(str(path)), []
    fps = cap.get(cv2.CAP_PROP_FPS) or 16
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        out.append(core.extract_metrics(res.pose_landmarks.landmark) if res.pose_landmarks else None)
    cap.release()
    return out, fps


def verdict(posture, metrics, ref, fps):
    """(C14a, C14b ou C14c, detail) pour une video."""
    seen = [m for m in metrics if m]
    a = len(seen) >= SEEN_MIN * len(metrics)
    devs = [core.deviations(m, ref) for m in seen]
    if posture == "droit2":
        calm = [abs(d[4]) < THIRD[0] and d[2] < THIRD[1] and abs(d[3]) < THIRD[2] for d in devs]
        return a, sum(calm) >= OK_MIN * len(calm), f"max raccourc. {max(abs(d[4]) for d in devs):.3f}, " \
            f"cou {max(d[2] for d in devs):.1f}, largeur {max(abs(d[3]) for d in devs):.3f}"
    last = [core.deviations(m, ref)[4] for m in metrics[-int(fps):] if m]
    high = sum(v > core.POSTURE_THRESHOLD for v in last)
    return a, bool(last) and high >= OK_MIN * len(last), f"derniere seconde : raccourc. median " \
        f"{sorted(last)[len(last) // 2] if last else float('nan'):+.3f}, {high}/{len(last)} images > seuil"


def main():
    root = Path(sys.argv[1])
    people = sys.argv[sys.argv.index("--personnes") + 1].split(",") if "--personnes" in sys.argv else ["1"]
    model = sys.argv[sys.argv.index("--modele") + 1] if "--modele" in sys.argv else MODEL
    videos = root / f"videos_{model.split('/')[1].lower()}"
    videos.mkdir(exist_ok=True)
    load_dotenv(".env")
    token = os.getenv("HF_TOKEN") or sys.exit("HF_TOKEN absent du .env")
    provider = sys.argv[sys.argv.index("--fournisseur") + 1] if "--fournisseur" in sys.argv else "fal-ai"
    client = InferenceClient(provider=provider, api_key=token, bill_to=os.getenv("HF_BILL_TO") or None, timeout=900)

    def make(job):
        n, posture = job
        path = videos / f"{posture}_{n}.mp4"
        if not path.exists():
            try:
                path.write_bytes(client.image_to_video(
                    (root / "photos" / f"droit_{n}.jpg").read_bytes(), model=model, prompt=CLIPS[posture] + STILL,
                    negative_prompt=NEGATIVE, seed=0, **EXTRA.get(provider, {})))
            except Exception as e:  # une video en echec ne bloque pas les autres
                return f"{path.name} : echec ({str(e)[:200]})"
        return f"{path.name} : ok"

    with ThreadPoolExecutor(3) as ex:
        for line in ex.map(make, [(n, p) for n in people for p in CLIPS]):
            print(line, flush=True)

    with mp.solutions.pose.Pose(static_image_mode=False, min_detection_confidence=0.5) as video_pose, \
            mp.solutions.pose.Pose(static_image_mode=True) as photo_pose:
        for n in people:
            for posture in CLIPS:
                path = videos / f"{posture}_{n}.mp4"
                if not path.exists():
                    continue
                ok, first = cv2.VideoCapture(str(path)).read()  # calibration : 1re image (recadree en 16:9)
                res = photo_pose.process(cv2.cvtColor(first, cv2.COLOR_BGR2RGB))
                ref = core.extract_metrics(res.pose_landmarks.landmark)
                metrics, fps = frames_metrics(path, video_pose)
                a, bc, detail = verdict(posture, metrics, ref, fps)
                crit = "C14b" if posture == "droit2" else "C14c"
                print(f"{path.name:18} {len(metrics)} images a {fps:.0f}/s  C14a {'OK' if a else 'non'}  "
                      f"{crit} {'OK' if bc else 'non'}  ({detail})")


if __name__ == "__main__":
    main()
