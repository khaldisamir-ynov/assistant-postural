"""Photos -> reperes MediaPipe au format de enregistrer.py, pour noter des images (generees ou reelles) avec rejouer.py.

Chaque photo devient une posture tenue 12 s (la meme image repetee a 10 images/s) : le banc applique ainsi la vraie
logique (calibration sur « droit », delai d'alerte). Photos <posture>_<n>.jpg : une serie par n (une personne generee,
ou une prise de enregistrer.py --photos), ecrite dans <dossier>/serie_<n>/landmarks.jsonl.
Limite : image fixe, donc aucun bruit ; le critere de bruit immobile (CA3) n'a pas de sens sur ces series.

Usage : .venv\\Scripts\\python essais\\images_vers_reperes.py essais\\donnees\\genere
Puis : .venv\\Scripts\\python essais\\rejouer.py essais\\donnees\\genere\\serie_*\\landmarks.jsonl
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import mediapipe as mp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from posture import core  # noqa: E402

RECORD, FRAME_PERIOD = 12, 0.1  # comme enregistrer.py et le detecteur


def main():
    folder = Path(sys.argv[1])
    series = defaultdict(dict)
    for p in sorted((folder / "photos").glob("*.jpg")):
        posture, n = p.stem.rsplit("_", 1)
        series[n][posture] = p
    if not series:
        sys.exit(f"Aucune photo dans {folder / 'photos'}")
    missed = []
    with mp.solutions.pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
        for n, photos in series.items():
            rows = {}
            for posture, path in photos.items():
                res = pose.process(cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB))
                lm = res.pose_landmarks.landmark if res.pose_landmarks else None
                if lm and core.extract_metrics(lm):
                    rows[posture] = [[round(p.x, 4), round(p.y, 4), round(p.z, 4), round(p.visibility, 3)] for p in lm]
                else:
                    missed.append(path.name)  # tete ou epaules non vues : le detecteur dirait « absent »
            if "droit" not in rows:
                print(f"serie {n} : « droit » absent ou non vu par MediaPipe, pas de calibration possible, ignoree")
                continue
            out = folder / f"serie_{n}"
            out.mkdir(exist_ok=True)
            with open(out / "landmarks.jsonl", "w") as f:
                for posture, row in rows.items():
                    for k in range(int(RECORD / FRAME_PERIOD)):
                        f.write(json.dumps({"posture": posture, "t": round(k * FRAME_PERIOD, 2), "lm": row}) + "\n")
            print(f"serie {n} : {out / 'landmarks.jsonl'}")
    total = sum(len(p) for p in series.values())
    print(f"\nMediaPipe : tete et epaules trouvees sur {total - len(missed)}/{total} photos"
          + (f" ; manquees : {', '.join(missed)}" if missed else ""))


if __name__ == "__main__":
    main()
