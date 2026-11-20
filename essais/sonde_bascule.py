"""Sonde C15 (SPECIFICATIONS.md § 4.10) : avachi = epaules qui descendent sans que la tete bascule.

Ecarts a la calibration « droit » 4-7 s, image par image, sans les 2 premieres secondes de chaque posture :
  descente : descente des epaules en largeurs d'epaules (ancienne detection « epaules »)
  bascule  : (y du nez - y du milieu des oreilles) / ecart des yeux, ecart signe (positif = le nez descend)
Regle : avachi si descente > s et bascule < b. C15a : un couple (s, b) qui passe dans chaque enregistrement ;
C15b : le couple choisi sur les autres enregistrements passe sur celui qui a ete laisse de cote.
Usage : .venv\\Scripts\\python essais\\sonde_bascule.py essais\\donnees\\2026-10-30\\landmarks.jsonl [autres...]
"""
import json
import math
import statistics
import sys

BONNES, MAUVAISE = ("droit", "droit2", "clavier"), "avache"
GOOD_MAX, BAD_MIN = 0.10, 0.90
S_GRID = [i / 200 for i in range(4, 21)]       # 2 % a 10 %, pas de 0,5 %
B_GRID = [i / 20 for i in range(-10, 13)]      # -0,5 a +0,6 ecart d'yeux, pas de 0,05


def mesures(lm):
    eyes = math.dist(lm[2][:2], lm[5][:2])
    return {"sh_y": (lm[11][1] + lm[12][1]) / 2, "w": abs(lm[11][0] - lm[12][0]),
            "pitch": (lm[0][1] - (lm[7][1] + lm[8][1]) / 2) / eyes}


def charger(path):
    """{posture: [(descente, bascule), ...]} pour un enregistrement."""
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    rows = [r for r in rows if r.get("lm") and min(r["lm"][i][3] for i in (0, 2, 5, 7, 8, 11, 12)) >= 0.5]
    cal = [mesures(r["lm"]) for r in rows if r["posture"] == "droit" and 4 <= r["t"] < 7]
    ref = {k: statistics.median(c[k] for c in cal) for k in cal[0]}
    out = {}
    for r in rows:
        if r["t"] >= 2 and r["posture"] in BONNES + (MAUVAISE,):
            m = mesures(r["lm"])
            out.setdefault(r["posture"], []).append(((m["sh_y"] - ref["sh_y"]) / ref["w"], m["pitch"] - ref["pitch"]))
    return out


def taux(images, s, b):
    return sum(d > s and p < b for d, p in images) / len(images)


def marge(session, s, b):
    """> 0 : le couple remplit les seuils sur cet enregistrement ; plus c'est grand, plus il y a de reserve."""
    return min(taux(session[MAUVAISE], s, b) - BAD_MIN,
               min(GOOD_MAX - taux(session[p], s, b) for p in BONNES))


def meilleur(sessions):
    return max(((s, b) for s in S_GRID for b in B_GRID), key=lambda sb: min(marge(x, *sb) for x in sessions))


def main(paths):
    data = {p.split("donnees")[-1].strip("\\/").split("\\")[0].split("/")[0]: charger(p) for p in paths}
    print(f"{'enregistrement':22}{'posture':10}{'descente med.':>15}{'bascule med.':>14}")
    for name, sess in data.items():
        for posture, images in sess.items():
            print(f"{name:22}{posture:10}{statistics.median(d for d, _ in images):>15.3f}"
                  f"{statistics.median(p for _, p in images):>14.3f}")

    # C15a : un couple commun aux 4 enregistrements
    s, b = meilleur(list(data.values()))
    pire = min(marge(x, s, b) for x in data.values())
    print(f"\nC15a : meilleur couple commun s = {s:.3f}, b = {b:+.2f}, marge la plus faible {pire:+.2f}")
    for name, sess in data.items():
        print(f"  {name:22} avache {100 * taux(sess[MAUVAISE], s, b):3.0f} %  "
              + "  ".join(f"{p} {100 * taux(sess[p], s, b):3.0f} %" for p in BONNES))
    c15a = pire >= 0
    print(f"C15a : {'ATTEINT' if c15a else 'NON ATTEINT'}")

    # C15b : choisi sur les autres, juge sur celui laisse de cote
    c15b = True
    print("\nC15b : couple choisi sur les autres enregistrements, juge sur celui laisse de cote")
    for name, sess in data.items():
        s, b = meilleur([x for n, x in data.items() if n != name])
        ok = marge(sess, s, b) >= 0
        c15b &= ok
        print(f"  {name:22} s = {s:.3f}, b = {b:+.2f} : avache {100 * taux(sess[MAUVAISE], s, b):3.0f} %, "
              + ", ".join(f"{p} {100 * taux(sess[p], s, b):.0f} %" for p in BONNES) + f"  {'OK' if ok else 'ECHEC'}")
    print(f"C15b : {'ATTEINT' if c15b else 'NON ATTEINT'}")


if __name__ == "__main__":
    main(sys.argv[1:])
