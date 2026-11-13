"""Sonde : nouvelles mesures des epaules en avant (enroulees), sur les enregistrements existants.

Ecarts a la calibration « droit » 4-7 s, par posture : mediane et part des images au-dessus du seuil.
  actuel  : descente des epaules en largeurs d'epaules (detection « Epaules » de l'appli), seuil 5 %
  etroit  : resserrement des epaules, largeur rapportee a l'ecart des yeux (insensible a la distance), seuil 5 %
  z       : epaules qui avancent vers la camera par rapport aux oreilles (profondeur MediaPipe), en largeurs, seuil 0.05
Usage : .venv\\Scripts\\python essais\\sonde_epaules.py essais\\donnees\\2026-11-13-bureau-c\\landmarks.jsonl [autres...]
"""
import json
import math
import statistics
import sys


def mesures(lm):
    w = abs(lm[11][0] - lm[12][0])
    return {"sh_y": (lm[11][1] + lm[12][1]) / 2, "w": w, "etroit": w / math.dist(lm[2][:2], lm[5][:2]),
            "z": ((lm[7][2] + lm[8][2]) - (lm[11][2] + lm[12][2])) / 2 / w}


def ecarts(c, r):
    return {"actuel": (c["sh_y"] - r["sh_y"]) / r["w"], "etroit": 1 - c["etroit"] / r["etroit"], "z": c["z"] - r["z"]}


SEUILS = {"actuel": 0.05, "etroit": 0.05, "z": 0.05}
for path in sys.argv[1:]:
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    rows = [r for r in rows if r.get("lm") and min(r["lm"][i][3] for i in (2, 5, 7, 8, 11, 12)) >= 0.5]
    cal = [mesures(r["lm"]) for r in rows if r["posture"] == "droit" and 4 <= r["t"] < 7]
    ref = {k: statistics.median(c[k] for c in cal) for k in cal[0]}
    print(f"\n{path.split('donnees')[-1]}")
    print(f"{'posture':12}" + "".join(f"{k:>18}" for k in SEUILS))
    for posture in dict.fromkeys(r["posture"] for r in rows):
        ds = [ecarts(mesures(r["lm"]), ref) for r in rows if r["posture"] == posture and r["t"] >= 2]
        if ds:
            print(f"{posture:12}" + "".join(
                f"{statistics.median(d[k] for d in ds):>9.3f} ({100 * sum(d[k] > s for d in ds) / len(ds):3.0f}%)"
                for k, s in SEUILS.items()))
