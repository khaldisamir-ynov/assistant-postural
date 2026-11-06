"""Tri du jeu genere : ecarte les photos qui ne montrent pas ce que dit leur nom (criteres C10, SPECIFICATIONS.md).

Controles independants des VLM notes ensuite (un tri par VLM favoriserait ceux qui lui ressemblent) : MediaPipe Pose
(tete, epaules, main pres du visage) et MediaPipe ObjectDetector (telephone, boisson ; modele COCO EfficientDet-Lite2).
Rejets deplaces dans photos_rejetees/ (rien n'est supprime), motifs ajoutes a rejets.jsonl. Relancer
generer_images.py regenere les photos manquantes, puis relancer ce tri.

Usage : .venv\\Scripts\\python essais\\valider_images.py essais\\donnees\\genere
"""
import json
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from posture import core  # noqa: E402

# Lite2 (23 Mo) et non Lite0 (4 Mo) : essai du 2026-11-06, Lite0 prend 5 tasses sur 8 tenues a la bouche pour un telephone
MODEL = Path(__file__).resolve().parent / "donnees" / "modeles" / "efficientdet_lite2.tflite"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite2/float32/latest/"
             "efficientdet_lite2.tflite")
PHONE, DRINKS = {"cell phone"}, {"cup", "bottle", "wine glass"}
MIN_SCORE = 0.3
# Temoin droit2 (C10b) : la modification seule doit deplacer le corps de moins du tiers des seuils de l'application
MAX_SHORTENING, MAX_NECK, MAX_WIDTH = core.POSTURE_THRESHOLD / 3, core.LEAN_ANGLE / 3, core.CLOSE_THRESHOLD / 3


def verdict(posture, metrics, ref, hand, objects):
    """Motif de rejet, ou None si la photo est valable. ref : mesures de « droit » ; objects : noms COCO detectes."""
    if metrics is None:
        return "tete ou epaules non vues"
    phone, drink = bool(objects & PHONE), bool(objects & DRINKS)
    near = hand is not None and hand < core.HAND_THRESHOLD
    if posture == "telephone":
        return None if phone else "telephone non detecte"
    if posture == "boire":
        return None if drink else "boisson non detectee"
    if phone or drink:
        return "telephone ou boisson present"
    if posture == "menton_main":
        return None if near else "main loin du visage"
    if near:
        return "main pres du visage"
    if posture == "droit2":
        _, _, neck, width, shortening = core.deviations(metrics, ref)
        if abs(shortening) >= MAX_SHORTENING or neck >= MAX_NECK or abs(width) >= MAX_WIDTH:
            return f"corps deplace par la modification (raccourc. {shortening:+.3f}, cou {neck:.1f}, largeur {width:+.3f})"
    return None


def move(path, folder):
    """Deplace sans ecraser un rejet precedent du meme nom."""
    folder.mkdir(exist_ok=True)
    dest, k = folder / path.name, 1
    while dest.exists():
        dest, k = folder / f"{path.stem}.{k}{path.suffix}", k + 1
    path.rename(dest)


def main():
    root = Path(sys.argv[1])
    photos, rejected = root / "photos", root / "photos_rejetees"
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    series = defaultdict(dict)
    for p in sorted(photos.glob("*.jpg")):
        posture, n = p.stem.rsplit("_", 1)
        series[n][posture] = p
    detector = vision.ObjectDetector.create_from_options(vision.ObjectDetectorOptions(
        base_options=BaseOptions(model_asset_buffer=MODEL.read_bytes()), score_threshold=MIN_SCORE))
    kept, rejects = Counter(), []
    with mp.solutions.pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
        def measure(path):
            rgb = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)
            lm = res.pose_landmarks.landmark if res.pose_landmarks else None
            found = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)).detections
            return (core.extract_metrics(lm) if lm else None, core.hand_face_distance(lm) if lm else None,
                    {d.categories[0].category_name for d in found})

        for n, by_posture in series.items():
            # « droit » d'abord : rejetee, toute la serie part (les autres photos sont faites a partir d'elle)
            lost = None if "droit" in by_posture else "serie ecartee : pas de photo « droit »"
            ref = None
            for posture in sorted(by_posture, key=lambda p: p != "droit"):
                path = by_posture[posture]
                metrics, hand, objects = measure(path)
                ref = metrics if posture == "droit" else ref
                reason = lost or verdict(posture, metrics, ref, hand, objects)
                if posture == "droit" and reason:
                    lost = f"serie ecartee : droit rejetee ({reason})"
                if reason:
                    rejects.append({"photo": path.name, "motif": reason, "objets": sorted(objects),
                                    "main": hand and round(hand, 2), "date": date.today().isoformat()})
                    move(path, rejected)
                else:
                    kept[posture] += 1
    with open(root / "rejets.jsonl", "a", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rejects)
    for r in rejects:
        print(f"rejet  {r['photo']:18} {r['motif']}")
    gone = Counter(r["photo"].rsplit("_", 1)[0] for r in rejects)
    print("\n" + "\n".join(f"{p:12} valables {kept[p]:2}  rejetees {gone[p]:2}" for p in sorted(kept | gone)))
    print(f"Total : {sum(kept.values())} valables, {len(rejects)} rejetees (deplacees dans {rejected})")


if __name__ == "__main__":
    main()
