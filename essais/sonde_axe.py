"""Sonde : axe haut de la tete -> milieu des hanches (idee de l'utilisateur), sur les enregistrements existants.

Mesures (ecart a la calibration « droit » 4-7 s), par posture : mediane et part des images au-dessus du seuil.
  actuel  : raccourcissement haut de la tete -> epaules (mesure « posture » de l'appli), seuil 3 %
  long    : raccourcissement haut de la tete -> hanches
  incl    : inclinaison de l'axe tete -> hanches (degres)
  chute   : descente du haut de la tete dans l'image, en largeurs d'epaules
Usage : .venv\Scripts\python essais\sonde_axe.py essais\donnees\2026-11-13-bureau-c\landmarks.jsonl [autres...]
"""
import json, math, statistics, sys

def m(lm):
    p = lambda i: lm[i]
    ex, ey = (p(2)[0] + p(5)[0]) / 2, (p(2)[1] + p(5)[1]) / 2
    gap = math.dist(p(2)[:2], p(5)[:2])
    top = (ex, ey - 1.5 * gap)
    sh = ((p(11)[0] + p(12)[0]) / 2, (p(11)[1] + p(12)[1]) / 2)
    hip = ((p(23)[0] + p(24)[0]) / 2, (p(23)[1] + p(24)[1]) / 2)
    w = abs(p(11)[0] - p(12)[0])
    return {"actuel": (sh[1] - top[1]) / w, "long": (hip[1] - top[1]) / w,
            "incl": math.degrees(math.atan2(top[0] - hip[0], hip[1] - top[1])), "top": top[1], "w": w,
            "hipvis": min(p(23)[3], p(24)[3]), "hipy": hip[1]}

def dev(c, r):
    return {"actuel": 1 - c["actuel"] / r["actuel"], "long": 1 - c["long"] / r["long"],
            "incl": abs(c["incl"] - r["incl"]), "chute": (c["top"] - r["top"]) / r["w"]}

SEUILS = {"actuel": 0.03, "long": 0.03, "incl": 3.0, "chute": 0.05}
for path in sys.argv[1:]:
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    rows = [r for r in rows if r.get("lm") and min(r["lm"][i][3] for i in (2, 5, 11, 12)) >= 0.5]
    cal = [m(r["lm"]) for r in rows if r["posture"] == "droit" and 4 <= r["t"] < 7]
    ref = {k: statistics.median(c[k] for c in cal) for k in cal[0]}
    print(f"\n{path.split('donnees')[-1]}  (hanches y ref {ref['hipy']:.2f}, visibilite {ref['hipvis']:.2f})")
    print(f"{'posture':12}" + "".join(f"{k:>18}" for k in SEUILS) + "   vis.hanches")
    for posture in dict.fromkeys(r["posture"] for r in rows):
        ds = [dev(m(r["lm"]), ref) for r in rows if r["posture"] == posture and r["t"] >= 2]
        vis = statistics.median(m(r["lm"])["hipvis"] for r in rows if r["posture"] == posture)
        cells = "".join(f"{statistics.median(d[k] for d in ds):>9.3f} ({100 * sum(d[k] > s for d in ds) / len(ds):3.0f}%)"
                        for k, s in SEUILS.items())
        print(f"{posture:12}{cells}   {vis:.2f}")
