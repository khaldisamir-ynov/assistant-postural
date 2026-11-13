"""MediaPipe, VLM ou LLM ? Comparaison sur les memes photos reelles (criteres C11, SPECIFICATIONS.md § 4.6).

A : MediaPipe + seuils de l'application (detector.update_status) ; B : VLM, photo seule ; C : VLM, photo de reference
« droit » + photo courante ; D : LLM texte, reperes MediaPipe (des nombres, comme le coach) ; E : A, puis B confirme
ou annule chaque alerte de A (calcule a partir des reponses de B, sans appel de plus).
Reference = droit_0 de chaque dossier, pour toutes les approches ; droit_0 n'est donc pas notee.

ATTENTION : les photos sont envoyees aux fournisseurs du routeur HF (essai seulement, avec l'accord de la personne).
Usage : .venv\\Scripts\\python essais\\comparer_approches.py essais\\donnees\\D1 [D2 ...] [--passe 2] [--modeles a,b]
Reponses brutes dans <dossier>/approches.jsonl : une relance ne refait que les appels absents. --passe 2 refait tout
une 2e fois (stabilite). Synthese ecrite dans essais/donnees/comparaison.json (page de rapport).
"""
import json
import math
import os
import statistics
import sys
import threading
import time
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import cv2
import mediapipe as mp
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comparer_vlm import data_url, parse  # noqa: E402
from posture import coach, core, detector  # noqa: E402
from posture.state import state  # noqa: E402
from rejouer import settings_for  # noqa: E402

CLASSES = ("correcte", "affaissee", "penchee", "trop_pres", "menton_main")
# Consigne de enregistrer.py -> classe attendue ; telephone et boire : rapportes a part, non notes
LABELS = {"droit": "correcte", "droit2": "correcte", "clavier": "correcte", "tete_avant": "affaissee",
          "avache": "affaissee", "penche": "penchee", "trop_pres": "trop_pres", "menton_main": "menton_main"}
MAIN_TASK = {"droit", "droit2", "clavier", "tete_avant", "avache", "penche"}  # detections actives par defaut
VLMS = ["Qwen/Qwen3-VL-30B-A3B-Instruct", "google/gemma-4-26B-A4B-it"]
LLMS = {coach.MODEL.split(":")[0]: "none", "openai/gpt-oss-120b": "low"}  # modele -> effort de reflexion
PERIOD = 5  # s entre deux analyses si B, C ou D remplacaient MediaPipe (cout horaire)
FALSE_MAX, LATENCY_MAX = 0.10, 3.0  # C11b, C11c
POINT_NAMES = ["nez", "oeil gauche (interieur)", "oeil gauche", "oeil gauche (exterieur)", "oeil droit (interieur)",
               "oeil droit", "oeil droit (exterieur)", "oreille gauche", "oreille droite", "bouche gauche",
               "bouche droite", "epaule gauche", "epaule droite", "coude gauche", "coude droit", "poignet gauche",
               "poignet droit"]
CHOICES = ("Reponds par un seul mot parmi : correcte ; affaissee (tete avancee vers l'ecran ou dos avachi, epaules "
           "tombantes) ; penchee (tete ou buste incline sur le cote, accoude) ; trop_pres (buste trop proche de "
           "l'ecran) ; menton_main (tete appuyee sur la main). Baisser les yeux vers le clavier en gardant le dos "
           "droit est une posture correcte.")
PROMPTS = {
    "B": "Photo prise par la webcam d'une personne assise a son bureau. Quelle est sa posture ? " + CHOICES,
    "C": ("1re photo : posture de reference de cette personne, assise droite, prise par sa webcam. 2e photo : la "
          "meme personne maintenant, meme webcam. Par rapport a la reference, quelle est sa posture ? " + CHOICES),
    "D": ("Reperes du corps d'une personne assise a son bureau, vue de face par sa webcam (detecteur MediaPipe). "
          "Coordonnees normalisees x, y entre 0 et 1, y vers le bas, image en miroir. Reference (assise droite) :\n"
          "{ref}\nMaintenant :\n{cur}\nPar rapport a la reference, quelle est sa posture ? " + CHOICES),
}


def wilson(k, n, z=1.96):
    """Intervalle de confiance a 95 % d'une proportion k/n (fiable meme sur 20 photos ou a 0 %)."""
    if n == 0:
        return 0.0, 1.0
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def app_class(status):
    """Motif de l'application -> classe (priorites de update_status : trop pres masque les autres)."""
    for flag, cls in (("close", "trop_pres"), ("hand", "menton_main"), ("lean", "penchee"),
                      ("posture", "affaissee"), ("slouch", "affaissee"), ("head", "affaissee")):
        if status.get(flag):
            return cls
    return "correcte"


def scores(rows):
    """rows : (posture, classe predite). Rappel / fausses alertes sur la tache principale, exactitude du motif."""
    main = [(p, c) for p, c in rows if p in MAIN_TASK]
    bad = [c for p, c in main if LABELS[p] != "correcte"]
    good = [c for p, c in main if LABELS[p] == "correcte"]
    tp, fp = sum(c != "correcte" for c in bad), sum(c != "correcte" for c in good)
    labelled = [(LABELS[p], c) for p, c in rows if p in LABELS]
    return {"tp": tp, "bad": len(bad), "fp": fp, "good": len(good),
            "recall": tp / len(bad) if bad else 0, "recall_ci": wilson(tp, len(bad)),
            "false": fp / len(good) if good else 0, "false_ci": wilson(fp, len(good)),
            "motif": sum(t == c for t, c in labelled) / len(labelled) if labelled else 0, "n_motif": len(labelled),
            "confusion": {t: dict(Counter(c for tt, c in labelled if tt == t)) for t in CLASSES}}


def decide(r, a, sends_images):
    """Verdict C11 d'une approche r face a A (dictionnaires de scores, latence en s)."""
    if r is a:
        return "reference"
    overlap = lambda x, y: x[0] <= y[1] and y[0] <= x[1]  # noqa: E731
    fails = [name for name, ok in (("C11a rappel", r["recall"] >= a["recall"]), ("C11b fausses alertes",
             r["false"] <= FALSE_MAX), ("C11c latence", r["latency"] <= LATENCY_MAX)) if not ok]
    if fails:
        return "écartée (" + ", ".join(fails) + ")"
    if overlap(r["recall_ci"], a["recall_ci"]) and overlap(r["false_ci"], a["false_ci"]):
        return "équivalente à A : A gardée (rien ne sort du poste, hors ligne, gratuit)"
    return "option désactivée par défaut (C11d)" if sends_images else "meilleure que A"


def hybrid(a_rows, b_rows):
    """E : alerte de A gardee seulement si B voit aussi une mauvaise posture. rows : {photo: (posture, classe)}."""
    return {k: (p, c if c == "correcte" or b_rows.get(k, (p, "?"))[1] != "correcte" else "correcte")
            for k, (p, c) in a_rows.items()}


def describe(lm):
    return "\n".join(f"{name} : " + (f"x={p.x:.3f} y={p.y:.3f}" if p.visibility >= core.MIN_VISIBILITY else
                                    "non visible") for name, p in zip(POINT_NAMES, lm))


def measure(folders):
    """Reperes MediaPipe de chaque photo et temps de calcul. Retourne {photo: (posture, reperes ou None, s)}."""
    out = {}
    with mp.solutions.pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
        for folder in folders:
            for p in sorted((folder / "photos").glob("*.jpg")):
                rgb = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
                t0 = time.perf_counter()
                res = pose.process(rgb)
                lm = [SimpleNamespace(x=q.x, y=q.y, z=q.z, visibility=q.visibility)
                      for q in res.pose_landmarks.landmark] if res.pose_landmarks else None
                out[p] = (p.stem.rsplit("_", 1)[0], lm, time.perf_counter() - t0)
    return out


def run_app(photos, ref_lm, overrides):
    """Approche A : chaque photo jugee seule par update_status (pas de delai ni de lissage : voir rejouer.py)."""
    s = settings_for(list(core.extract_metrics(ref_lm)), overrides=overrides)
    out = {}
    for k, (posture, lm, _) in photos.items():
        m = core.extract_metrics(lm) if lm else None
        detector.update_status(m, s, None, 0.0, core.hand_face_distance(lm) if lm else None)
        out[k] = (posture, app_class(state.status) if m else "correcte")  # personne non vue : pas d'alerte
    return out


def prices():
    """Prix par million de jetons (entree, sortie) par (modele, fournisseur), d'apres le routeur."""
    data = json.load(urllib.request.urlopen("https://router.huggingface.co/v1/models", timeout=30))["data"]
    return {(m["id"], p["provider"]): (p["pricing"]["input"], p["pricing"]["output"])
            for m in data for p in m.get("providers", []) if p.get("pricing")}


def main():
    folders = [Path(a) for a in sys.argv[1:] if not a.startswith("--") and Path(a).is_dir()]
    passes = int(sys.argv[sys.argv.index("--passe") + 1]) if "--passe" in sys.argv else 1
    if "--modeles" in sys.argv:
        wanted = set(sys.argv[sys.argv.index("--modeles") + 1].split(","))
        vlms, llms = [m for m in VLMS if m in wanted], {m: e for m, e in LLMS.items() if m in wanted}
    else:
        vlms, llms = VLMS, LLMS
    if not folders:
        sys.exit(__doc__)
    load_dotenv(".env")
    token = os.getenv("HF_TOKEN") or sys.exit("HF_TOKEN absent du .env")
    bill_to = os.getenv("HF_BILL_TO")
    client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=token, max_retries=2, timeout=90,
                    default_headers={"X-HF-Bill-To": bill_to} if bill_to else None)

    measured = measure(folders)
    refs = {f: f / "photos" / "droit_0.jpg" for f in folders}
    for f, ref in refs.items():
        if ref not in measured or measured[ref][1] is None:
            sys.exit(f"{ref} absente ou personne non vue : reference impossible")
    scored = {k: v for k, v in measured.items() if k not in refs.values()}
    folder_of = {k: k.parent.parent for k in scored}

    # Appels : (approche, modele, photo, passe) ; reprise sur les journaux existants
    done, lock = {}, threading.Lock()
    for f in folders:
        log = f / "approches.jsonl"
        if log.exists():
            for line in open(log, encoding="utf-8"):
                r = json.loads(line)
                done[(r["approche"], r["modele"], r["photo"], r["passe"])] = r
    jobs = [(app, model, k, n) for n in range(1, passes + 1) for k in scored
            for app, models in (("B", vlms), ("C", vlms), ("D", list(llms))) for model in models
            if (app, model, str(k), n) not in done and (app != "D" or scored[k][1] is not None)]
    urls = {}

    def call(job):
        app, model, k, n = job
        if app == "D":
            content = PROMPTS["D"].format(ref=describe(measured[refs[folder_of[k]]][1][:17]),
                                          cur=describe(scored[k][1][:17]))
        else:
            for p in (k, refs[folder_of[k]]):
                urls.setdefault(p, data_url(p))
            images = ([urls[refs[folder_of[k]]]] if app == "C" else []) + [urls[k]]
            content = [{"type": "text", "text": PROMPTS[app]}] + [
                {"type": "image_url", "image_url": {"url": u}} for u in images]
        t0 = time.time()
        try:
            raw = client.chat.completions.with_raw_response.create(
                model=model, max_tokens=2000, temperature=0, reasoning_effort=llms.get(model, "none"),
                messages=[{"role": "user", "content": content}])
            r = raw.parse()
            text, provider = r.choices[0].message.content or "", raw.headers.get("x-inference-provider", "")
            usage = (r.usage.prompt_tokens, r.usage.completion_tokens) if r.usage else (0, 0)
            dt = time.time() - t0
        except Exception as e:  # modele indisponible, quota... : compte comme une mauvaise reponse
            text, provider, usage, dt = f"erreur : {e}", "", (0, 0), None
        row = {"approche": app, "modele": model, "photo": str(k), "passe": n, "reponse": text,
               "classe": parse(text, CLASSES), "s": dt, "jetons": usage, "fournisseur": provider}
        with lock:
            done[(app, model, str(k), n)] = row
            with open(folder_of[k] / "approches.jsonl", "a", encoding="utf-8") as log:
                log.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(".", end="", flush=True)

    print(f"{len(scored)} photos notees, {len(jobs)} appels a faire")
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(call, jobs))

    # Synthese
    price = prices()
    results = []
    a_default, a_all = {}, {}
    for f in folders:
        ref_lm = measured[refs[f]][1]
        mine = {k: v for k, v in scored.items() if folder_of[k] == f}
        a_default.update(run_app(mine, ref_lm, None))  # detections actives par defaut (tache principale)
        a_all.update(run_app(mine, ref_lm, {"detect_close": True, "detect_hand": True}))  # motif
    sa = scores(list(a_default.values()))
    sa.update({k: v for k, v in scores(list(a_all.values())).items() if k in ("motif", "confusion", "n_motif")})
    sa.update(latency=statistics.median(v[2] for v in scored.values()), latency_p95=0, cost_hour=0,
              leaves="rien", offline=True)
    results.append({"id": "A", "approche": "MediaPipe + seuils", "modele": "MediaPipe Pose", **sa})
    for app, models in (("B", vlms), ("C", vlms), ("D", list(llms))):
        for model in models:
            rows = [done.get((app, model, str(k), 1)) for k in scored]
            # D sans reperes (personne non vue par MediaPipe) : pas d'alerte, comme A
            preds = {k: (scored[k][0], r["classe"] if r else "correcte" if app == "D" else "?")
                     for k, r in zip(scored, rows)}
            ok = [r for r in rows if r and r["s"] is not None]
            times = sorted(r["s"] for r in ok)
            costs = [sum(t * p / 1e6 for t, p in zip(r["jetons"], price.get((model, r["fournisseur"]), (0, 0))))
                     for r in ok]
            sc = scores(list(preds.values()))
            second = [(done.get((app, model, str(k), 1)), done.get((app, model, str(k), 2))) for k in scored]
            pairs = [(x["classe"], y["classe"]) for x, y in second if x and y]
            sc.update(latency=statistics.median(times) if times else float("inf"),
                      latency_p95=times[int(0.95 * (len(times) - 1))] if times else float("inf"),
                      cost_call=statistics.mean(costs) if costs else 0,
                      cost_hour=(statistics.mean(costs) if costs else 0) * 3600 / PERIOD,
                      errors=len(rows) - len(ok), unparsed=sum(c == "?" for _, c in preds.values()),
                      stability=sum(x == y for x, y in pairs) / len(pairs) if pairs else None,
                      leaves="des nombres" if app == "D" else "la photo" if app == "B" else "2 photos", offline=False,
                      others={p: dict(Counter(c for k, (pp, c) in preds.items() if pp == p))
                              for p in ("telephone", "boire")})
            results.append({"id": app, "approche": {"B": "VLM, photo seule", "C": "VLM, référence + photo",
                                                    "D": "LLM, repères (texte)"}[app], "modele": model, **sc})
            if app == "B":
                e = hybrid(a_default, preds)
                se = scores(list(e.values()))
                alerts = [k for k, (_, c) in a_default.items() if c != "correcte"]
                e_times = sorted(r["s"] for k, r in zip(scored, rows) if r and r["s"] is not None and k in alerts)
                se.update(latency=statistics.median(e_times) if e_times else 0, latency_p95=0, cost_hour=None,
                          cost_call=sc["cost_call"], leaves="1 photo par alerte", offline=False,
                          motif=sa["motif"], confusion=sa["confusion"], n_motif=sa["n_motif"])
                results.append({"id": "E", "approche": "MediaPipe, puis VLM confirme", "modele": model, **se})
    for r in results:
        if r["id"] == "E":  # C11 pour E : moins de fausses alertes sans perdre une vraie
            r["verdict"] = ("retenue en option" if r["fp"] < sa["fp"] and r["tp"] == sa["tp"]
                            else "écartée (" + ("perd une vraie alerte" if r["tp"] < sa["tp"]
                                                 else "aucune fausse alerte en moins") + ")")
        else:
            r["verdict"] = decide(r, results[0], r["id"] in "BC")

    print(f"\n\n{'':2}{'approche':30} {'modele':34} {'rappel':>14} {'fausses al.':>14} {'motif':>6} "
          f"{'lat.':>6} {'$/h':>6}  verdict")
    for r in results:
        cost = "-" if r["cost_hour"] is None else f"{r['cost_hour']:.2f}"
        print(f"{r['id']:2}{r['approche']:30} {r['modele'][:34]:34} {r['tp']:3}/{r['bad']:<3}({r['recall']:4.0%}) "
              f"{r['fp']:3}/{r['good']:<3}({r['false']:4.0%}) {r['motif']:6.0%} {r['latency']:5.2f}s {cost:>6}  "
              f"{r['verdict']}")
    out = Path(__file__).resolve().parent / "donnees" / "comparaison.json"
    out.write_text(json.dumps({"dossiers": [str(f) for f in folders], "photos": len(scored), "periode_s": PERIOD,
                               "resultats": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSynthese : {out}")


if __name__ == "__main__":
    main()
