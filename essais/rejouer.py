"""Banc d'essai : rejoue un essai enregistre dans la vraie logique de detection et verifie les criteres d'acceptation.

Usage : .venv\\Scripts\\python essais\\rejouer.py essais\\donnees\\AAAA-MM-JJ\\landmarks.jsonl [autres...] [--etape 2]
                 [--seuil 0.03] [--angle 6]
Plusieurs essais (motifs acceptes, ex. essais\\donnees\\genere\\serie_*\\landmarks.jsonl) : un bilan par essai, puis
le total d'echecs, a comparer avant et apres chaque modification.
--etape N : detections des etapes 1 a N actives, postures de ces etapes notees (defaut : derniere etape).
Reglages : valeurs par defaut de l'application (posture/state.py) ; --seuil / --angle remplacent les tolerances.
Criteres (specifications-assistant-postural.docx) :
    CA1 bonne posture -> aucune alerte et au plus 10 % des images signalees
    CA2 mauvaise posture -> au moins une alerte, le bon motif sur au moins 90 % des images, un faux motif sur 10 % au plus
    CA3 personne immobile -> bruit de chaque parametre actif inferieur au tiers de sa tolerance
"""
import argparse
import glob
import json
import statistics
import sys
from collections import Counter, deque
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from posture import core, detector  # noqa: E402
from posture.state import DEFAULTS, state  # noqa: E402

REASONS = ("posture", "head", "lean", "close", "hand", "axis")
# Par etape : detection activee (reglage, tolerance) et postures notees -> (motifs requis, motifs admis en plus)
STEPS = {
    1: ("detect_posture", "posture_threshold", {
        "droit": (set(), set()), "droit2": (set(), set()), "clavier": (set(), set()),
        "tete_avant": ({"posture"}, set()), "avache": ({"posture"}, set())}),
    # se pencher raccourcit aussi la hauteur tete-epaules : le motif « posture » y est admis
    2: ("detect_lean", "lean_angle", {"penche": ({"lean"}, {"posture"})}),
}
LAST_STEP = max(STEPS)
CALIBRATION = (4.0, 7.0)  # secondes de « droit » utilisees comme calibration (installe, immobile)
GOOD_MAX, BAD_MIN = 0.10, 0.90


def landmarks(row):
    return [SimpleNamespace(x=p[0], y=p[1], z=p[2], visibility=p[3]) for p in row["lm"]]


def reference(rows):
    """Comme detector.update_status : mediane des mesures de la fenetre de calibration."""
    calib = [m for r in rows for m in [core.extract_metrics(landmarks(r))] if m]
    if not calib:
        sys.exit("Aucune mesure dans la fenêtre de calibration : essai vide ou personne hors champ.")
    return [statistics.median(m[i] for m in calib) for i in range(len(calib[0]))]


def settings_for(ref, step=LAST_STEP, overrides=None):
    """Reglages par defaut, avec exactement les detections des etapes 1 a step."""
    s = {**DEFAULTS, "places": {"essai": [ref]}, "place": "essai"}
    s.update({flag: n <= step for n, (flag, _, _) in STEPS.items()})
    return {**s, **(overrides or {})}


def expected_for(step):
    out = {}
    for n in range(1, step + 1):
        out.update(STEPS[n][2])
    return out


def simulate(rows, settings):
    """Rejoue des images dans update_status (memes lissages que detector._loop). Retourne les statistiques."""
    recent, recent_hand = deque(maxlen=detector.SMOOTHING_FRAMES), deque(maxlen=detector.SMOOTHING_FRAMES)
    bad_since, prev = None, None
    out = {"n": len(rows), "flagged": 0, "alerts": 0, "reasons": Counter(), "dev": {"posture": [], "lean": []}}
    for r in rows:
        lm = landmarks(r)
        m = core.extract_metrics(lm)
        recent.append(m) if m else recent.clear()
        recent_hand.append(core.hand_face_distance(lm))
        seen = [d for d in recent_hand if d is not None]
        hand = statistics.median(seen) if len(seen) * 2 >= len(recent_hand) else None
        smoothed = tuple(sum(v) / len(recent) for v in zip(*recent)) if recent else None
        bad_since = detector.update_status(smoothed, settings, bad_since, r["t"], hand)
        st = state.status
        for name, values in out["dev"].items():
            if f"{name}_dev" in st:
                values.append(st[f"{name}_dev"])
        if st["state"] in ("bad", "alert"):
            out["flagged"] += 1
            out["reasons"].update(k for k in REASONS if st.get(k))
        out["alerts"] += st["state"] == "alert" and prev != "alert"
        prev = st["state"]
    return out


def verdict(o, required, allowed):
    """CA1 si aucun motif requis, sinon CA2. Retourne (ok, detail)."""
    if not required:
        return o["alerts"] == 0 and o["flagged"] / o["n"] <= GOOD_MAX, ""
    missing = [k for k in required if o["reasons"][k] / o["n"] < BAD_MIN]
    wrong = [k for k in o["reasons"] if k not in required | allowed and o["reasons"][k] / o["n"] > GOOD_MAX]
    detail = ", ".join([f"{k} < 90 %" for k in missing] + [f"faux motif {k}" for k in wrong])
    return o["alerts"] >= 1 and not missing and not wrong, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fichiers", nargs="+")
    ap.add_argument("--etape", type=int, default=LAST_STEP, choices=sorted(STEPS))
    ap.add_argument("--seuil", type=float, help="tolerance de l'etape 1 (raccourcissement, ex. 0.03)")
    ap.add_argument("--angle", type=float, help="tolerance de l'etape 2 (degres, ex. 6)")
    args = ap.parse_args()
    files = [f for pattern in args.fichiers for f in sorted(glob.glob(pattern)) or [pattern]]  # PowerShell ne developpe pas *
    results = {f: bench(f, args) for f in files}
    if len(files) > 1:
        print("\n=== Bilan ===")
        for f, failures in results.items():
            print(f"{failures} échec(s)  {f}")
        print(f"Total : {sum(results.values())} critère(s) non atteint(s) sur {len(files)} essais, "
              f"{sum(not v for v in results.values())} essai(s) sans échec")


def bench(path, args):
    """Rejoue un essai et affiche son detail. Retourne le nombre de criteres non atteints."""
    print(f"\n### {path}")
    overrides = {k: v for k, v in (("posture_threshold", args.seuil), ("lean_angle", args.angle)) if v}
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    ref = reference([r for r in rows if r["posture"] == "droit" and CALIBRATION[0] <= r["t"] < CALIBRATION[1]])
    s = settings_for(ref, args.etape, overrides)
    active = [STEPS[n] for n in STEPS if n <= args.etape]
    print(f"Étapes 1 à {args.etape} : " + ", ".join(f"{tol} = {s[tol]}" for _, tol, _ in active) + "\n")

    expected = expected_for(args.etape)
    print(f"{'posture':12s} {'attendu':14s} {'signalée':>8s} {'alertes':>7s}  {'verdict':8s} motifs")
    failures = 0
    for posture in dict.fromkeys(r["posture"] for r in rows):
        o = simulate([r for r in rows if r["posture"] == posture], s)
        if posture in expected:
            required, allowed = expected[posture]
            ok, detail = verdict(o, required, allowed)
            failures += not ok
            label, result = ", ".join(sorted(required)) or "aucune alerte", ("OK" if ok else "ÉCHEC") + (f" ({detail})" if detail else "")
        else:
            label, result = "non noté", ""
        reasons = {k: f"{100 * v / o['n']:.0f} %" for k, v in o["reasons"].items()}
        print(f"{posture:12s} {label:14s} {100 * o['flagged'] / o['n']:7.0f} % {o['alerts']:7d}  {result:8s} {reasons}")

    # CA3 : bruit de chaque parametre actif en posture droite, apres la calibration
    still = simulate([r for r in rows if r["posture"] == "droit" and r["t"] >= CALIBRATION[1]], s)
    for name, tol in (("posture", "posture_threshold"), ("lean", "lean_angle")):
        if not s[{"posture": "detect_posture", "lean": "detect_lean"}[name]]:
            continue
        noise = statistics.pstdev(still["dev"][name])
        ok = noise < s[tol] / 3
        failures += not ok
        print(f"\nCA3 bruit immobile ({name}) : écart-type {noise:.3f} (limite {s[tol] / 3:.3f}) -> {'OK' if ok else 'ÉCHEC'}", end="")
    print(f"\n\n{failures} critère(s) non atteint(s)")
    return failures


if __name__ == "__main__":
    main()
