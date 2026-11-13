"""Idee « deux points choisis sur le corps » (criteres C12, SPECIFICATIONS.md § 4.7) : pour chaque paire de points,
le segment raccourcit-il quand on s'affaisse, et seulement alors ?

Mesure : longueur du segment / largeur des epaules, raccourcissement relatif a la calibration (comme l'application),
moyenne glissante de 10 images (comme detector._loop). Une paire est valable s'il existe UN seuil auquel tete en avant
et avachi sont signales sur >= 90 % des images et droit2, clavier sur <= 10 %, dans CHAQUE enregistrement, avec un
bruit immobile sous le tiers de ce seuil. Classement : marge / bruit. Hors ligne, aucun appel reseau.

Usage : .venv\\Scripts\\python essais\\scanner_paires.py essais\\donnees\\2026-10-30\\landmarks.jsonl [autres...]
"""
import itertools
import json
import statistics
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from posture import core, detector  # noqa: E402
from rejouer import CALIBRATION, GOOD_MAX, BAD_MIN, landmarks  # noqa: E402

BAD, GOOD = ("tete_avant", "avache"), ("droit2", "clavier")
HIPS_MIN_SEEN = 0.9  # hanches candidates seulement si visibles sur 90 % des images
NAMES = {0: "nez", 2: "oeil G", 5: "oeil D", 7: "oreille G", 8: "oreille D", 9: "bouche G", 10: "bouche D",
         11: "epaule G", 12: "epaule D", 13: "coude G", 14: "coude D", 15: "poignet G", 16: "poignet D",
         23: "hanche G", 24: "hanche D", "tete": "haut de la tete", "epaules": "milieu des epaules"}


def point(lm, key):
    """(x, y) d'un point, ou None s'il n'est pas visible. Points virtuels : haut de la tete, milieu des epaules."""
    if key == "tete":
        le, re = lm[core.LEFT_EYE], lm[core.RIGHT_EYE]
        if min(le.visibility, re.visibility) < core.MIN_VISIBILITY:
            return None
        gap = ((le.x - re.x) ** 2 + (le.y - re.y) ** 2) ** 0.5
        return (le.x + re.x) / 2, (le.y + re.y) / 2 - core.TOP_OF_HEAD * gap
    if key == "epaules":
        a, b = point(lm, core.LEFT_SHOULDER), point(lm, core.RIGHT_SHOULDER)
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) if a and b else None
    p = lm[key]
    return (p.x, p.y) if p.visibility >= core.MIN_VISIBILITY else None


def length(lm, a, b):
    """Longueur du segment a-b en largeurs d'epaules, ou None (point cache, vue de profil)."""
    pa, pb = point(lm, a), point(lm, b)
    width = abs(lm[core.LEFT_SHOULDER].x - lm[core.RIGHT_SHOULDER].x)
    if pa is None or pb is None or width < 0.01:
        return None
    return ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5 / width


def current(lm):
    """Mesure actuelle de l'application (hauteur verticale haut de la tete -> epaules), pour comparaison."""
    m = core.extract_metrics(lm)
    return m[4] if m else None


def shortenings(rows, f):
    """Raccourcissement lisse par posture : {posture: [valeurs]}, ou None si la calibration est impossible."""
    calib = [v for r in rows if r["posture"] == "droit" and CALIBRATION[0] <= r["t"] < CALIBRATION[1]
             for v in [f(r["lm"])] if v]
    if len(calib) < 10:
        return None
    ref, out = statistics.median(calib), {}
    for posture in dict.fromkeys(r["posture"] for r in rows):
        recent, values = deque(maxlen=detector.SMOOTHING_FRAMES), []
        for r in rows:
            if r["posture"] != posture:
                continue
            v = f(r["lm"])
            recent.append(v) if v else recent.clear()
            values.append(1 - statistics.mean(recent) / ref if recent else None)
        out[posture] = values
    return out


def quantile(values, q):
    v = sorted(x if x is not None else 0.0 for x in values)  # point cache : pas de signalement, compte comme 0
    return v[min(len(v) - 1, int(q * len(v)))]


def evaluate(recordings, f):
    """Seuil, marge, bruit et verdict C12 d'une mesure f(lm) sur tous les enregistrements."""
    lo = hi = noise = None
    for rows in recordings:
        s = shortenings(rows, f)
        if s is None or any(p not in s for p in BAD + GOOD + ("droit",)):
            return None
        good_hi = max(quantile(s[p], 1 - GOOD_MAX) for p in GOOD)  # 90 % des bonnes images sous ce niveau
        bad_lo = min(quantile(s[p], 1 - BAD_MIN) for p in BAD)    # 90 % des mauvaises au-dessus
        sd = statistics.pstdev(v for v in s["droit"] if v is not None)
        lo, hi = max(lo, good_hi) if lo is not None else good_hi, min(hi, bad_lo) if hi is not None else bad_lo
        noise = max(noise, sd) if noise is not None else sd
    threshold, margin = (lo + hi) / 2, hi - lo
    return {"seuil": threshold, "marge": margin, "bruit": noise, "score": margin / max(noise, 1e-4),
            "C12a": margin > 0, "C12b": margin > 0 and noise < threshold / 3}


def main():
    files = [a for a in sys.argv[1:]]
    if not files:
        sys.exit(__doc__)
    recordings = [[{**r, "lm": landmarks(r)} for r in map(json.loads, open(p, encoding="utf-8"))] for p in files]
    hips_ok = all(sum(r["lm"][i].visibility >= core.MIN_VISIBILITY for r in rows) >= HIPS_MIN_SEEN * len(rows)
                  for rows in recordings for i in (23, 24))
    keys = [k for k in NAMES if k not in (23, 24) or hips_ok]
    results = [{"paire": "actuelle", "nom": "haut de la tete -> epaules (verticale, application)",
                **evaluate(recordings, current)}]
    for a, b in itertools.combinations(keys, 2):
        r = evaluate(recordings, lambda lm, a=a, b=b: length(lm, a, b))
        if r:
            results.append({"paire": [a, b], "nom": f"{NAMES[a]} -> {NAMES[b]}", **r})
    valid = sorted((r for r in results if r["C12a"] and r["C12b"]), key=lambda r: -r["score"])
    base = results[0]
    print(f"{len(results) - 1} paires testees sur {len(files)} enregistrement(s), hanches "
          f"{'candidates' if hips_ok else 'exclues (peu visibles)'} ; {len(valid)} paire(s) valable(s) (C12a et C12b)\n")
    print(f"{'mesure':48} {'seuil':>7} {'marge':>7} {'bruit':>7} {'score':>6}  C12")
    for r in [base] + [r for r in valid if r is not base][:15]:
        print(f"{r['nom']:48} {r['seuil']:+7.3f} {r['marge']:+7.3f} {r['bruit']:7.4f} {r['score']:6.1f}  "
              f"{'OK' if r['C12a'] and r['C12b'] else 'non'}")
    best = next((r for r in valid if r is not base), None)
    if best and best["score"] >= base["score"] or (best and not (base["C12a"] and base["C12b"])):
        print(f"\nPaire proposee par defaut : {best['nom']} {best['paire']}")
    else:
        print("\nAucune paire ne fait mieux que la mesure actuelle : elle reste par defaut")
    out = Path(__file__).resolve().parent / "donnees" / "paires.json"
    out.write_text(json.dumps({"fichiers": files, "resultats": [base] + valid}, ensure_ascii=False, indent=1),
                   encoding="utf-8")


if __name__ == "__main__":
    main()
