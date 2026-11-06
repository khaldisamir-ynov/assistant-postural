"""Essai « ordinateur deplace » (critere CA7) : rejoue l'essai dans la vraie logique de detection.

Usage : .venv\\Scripts\\python essais\\analyser_camera.py essais\\donnees\\AAAA-MM-JJ-camera\\camera.jsonl
                 [--etape 2] [--seuil 0.03] [--angle 6]
La personne reste droite pendant que l'ordinateur bouge : aucune alerte attendue, sauf a l'etape « avache ».
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rejouer import LAST_STEP, STEPS, reference, settings_for, simulate  # noqa: E402

CALIBRATION = (3.0, 6.0)  # secondes de l'etape « reference »
EXPECT_ALERT = {"avache"}  # etapes ou une alerte est attendue ; les autres doivent n'en declencher aucune


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fichier")
    ap.add_argument("--etape", type=int, default=LAST_STEP, choices=sorted(STEPS))
    ap.add_argument("--seuil", type=float)
    ap.add_argument("--angle", type=float)
    args = ap.parse_args()
    overrides = {k: v for k, v in (("posture_threshold", args.seuil), ("lean_angle", args.angle)) if v}
    rows = [json.loads(line) for line in open(args.fichier, encoding="utf-8")]
    ref = reference([r for r in rows if r["etape"] == "reference" and CALIBRATION[0] <= r["t"] < CALIBRATION[1]])
    s = settings_for(ref, args.etape, overrides)
    tolerances = ", ".join(f"{tol} = {s[tol]}" for n, (_, tol, _) in STEPS.items() if n <= args.etape)
    print(f"Étapes 1 à {args.etape} : {tolerances}\n")
    print(f"{'étape':16s} {'posture':>9s} {'cou':>7s} {'signalée':>8s} {'alertes':>7s}  verdict")
    failures = 0
    med = lambda v: statistics.median(v) if v else float("nan")  # noqa: E731
    for step in dict.fromkeys(r["etape"] for r in rows):
        o = simulate([r for r in rows if r["etape"] == step and (step != "reference" or r["t"] >= CALIBRATION[1])], s)
        ok = o["alerts"] >= 1 if step in EXPECT_ALERT else o["alerts"] == 0
        failures += not ok
        print(f"{step:16s} {100 * med(o['dev']['posture']):+8.1f}% {med(o['dev']['lean']):6.1f}° "
              f"{100 * o['flagged'] / o['n']:7.0f} % {o['alerts']:7d}  {'OK' if ok else 'ÉCHEC'}  {dict(o['reasons'])}")
    print(f"\nCA7 : {'OK' if not failures else f'ÉCHEC ({failures} étape(s))'}")


if __name__ == "__main__":
    main()
