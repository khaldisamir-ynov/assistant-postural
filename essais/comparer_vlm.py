"""Essai VLM « telephone / boisson » (priorite 4, criteres C9 de SPECIFICATIONS.md) : demande a des VLM du routeur
Hugging Face si la personne tient un telephone ou boit, sur les photos de enregistrer.py --photos.

ATTENTION : les photos sont envoyees aux fournisseurs du routeur HF (essai seulement, avec l'accord des personnes).
Usage : .venv\\Scripts\\python essais\\comparer_vlm.py essais\\donnees\\AAAA-MM-JJ [--modeles a,b]
Configuration : HF_TOKEN et HF_BILL_TO dans .env, comme mon_script.py. Reponses brutes ajoutees a vlm.jsonl.
"""
import base64
import json
import os
import statistics
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import cv2
from dotenv import load_dotenv
from openai import OpenAI

# Petits modeles d'abord (candidats a une version locale), puis les gros (borne haute)
MODELS = [
    "google/gemma-3-4b-it",
    "Qwen/Qwen3.5-9B",
    "zai-org/GLM-4.6V-Flash",
    "Qwen/Qwen3-VL-30B-A3B-Instruct",
    "google/gemma-4-26B-A4B-it",
    "Qwen/Qwen3-VL-235B-A22B-Instruct",
]
EXPECTED = {"telephone": "telephone", "boire": "boisson"}  # toutes les autres postures : « aucun »
ANSWERS = ("telephone", "boisson", "aucun")
PROMPT = ("Photo prise par la webcam d'une personne assise a son bureau. Tient-elle un telephone (en main ou a "
          "l'oreille), ou est-elle en train de boire (tasse, verre ou bouteille pres de la bouche) ? "
          "Reponds par un seul mot : telephone, boisson ou aucun.")
WIDTH = 512  # assez pour reconnaitre un objet tenu, et moins lourd a envoyer
FOUND_MIN, EXCUSED_MAX, LATENCY_MAX = 0.90, 0.05, 3.0  # C9a, C9b, C9c


def data_url(path):
    img = cv2.imread(str(path))
    img = cv2.resize(img, (WIDTH, round(img.shape[0] * WIDTH / img.shape[1])))
    return "data:image/jpeg;base64," + base64.b64encode(cv2.imencode(".jpg", img)[1]).decode()


def parse(text, answers=ANSWERS):
    """Premier mot attendu dans la reponse (accents, majuscules, espaces/tirets/_ ignores), « ? » sinon."""
    text = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().lower()
    text = text.replace(" ", "_").replace("-", "_")
    found = [(text.find(a), a) for a in answers if a in text]
    return min(found)[1] if found else "?"


def ask(client, model, url):
    t0 = time.time()
    r = client.chat.completions.create(
        # 1000 et non 20 : GLM-4.6V reflechit malgre reasoning_effort et rendait une reponse vide ; les autres
        # modeles s'arretent apres un mot
        model=model, max_tokens=1000, temperature=0,
        reasoning_effort="none",  # modeles qui reflechissent : sinon la reflexion consomme les tokens
        messages=[{"role": "user", "content": [
            {"type": "text", "text": PROMPT}, {"type": "image_url", "image_url": {"url": url}}]}])
    return r.choices[0].message.content or "", time.time() - t0


def report(model, rows):
    """rows : (posture, attendu, reponse, secondes ou None si erreur). Retourne la ligne de synthese."""
    by_posture = defaultdict(Counter)
    for posture, _, answer, _ in rows:
        by_posture[posture][answer] += 1
    print(f"\n== {model} ==")
    for posture, c in by_posture.items():
        print(f"  {posture:12} " + ", ".join(f"{a} {n}" for a, n in c.most_common()))
    objects = [r for r in rows if r[1] != "aucun"]
    others = [r for r in rows if r[1] == "aucun"]
    hits = sum(r[1] == r[2] for r in objects)
    wrong = sum(r[2] in EXPECTED.values() for r in others)
    found = hits / len(objects) if objects else 0
    excused = wrong / len(others) if others else 0
    times = [r[3] for r in rows if r[3] is not None]
    latency = statistics.median(times) if times else float("inf")
    ok = found >= FOUND_MIN and excused <= EXCUSED_MAX and latency <= LATENCY_MAX
    # effectifs affiches : sur une quinzaine de photos, une seule erreur fait varier le % de 6 points
    line = (f"{model:36} reconnus {hits:2}/{len(objects)} ({found:4.0%})  excuses a tort {wrong:2}/{len(others)} "
            f"({excused:4.0%})  latence {latency:4.1f} s  erreurs {len(rows) - len(times):2}  -> {'OK' if ok else 'non'}")
    print("  " + line)
    return line


def main():
    folder = Path(sys.argv[1])
    models = sys.argv[sys.argv.index("--modeles") + 1].split(",") if "--modeles" in sys.argv else MODELS
    photos = sorted((folder / "photos").glob("*.jpg"))
    if not photos:
        sys.exit(f"Aucune photo dans {folder / 'photos'} (lancer enregistrer.py --photos)")
    load_dotenv(".env")  # dossier courant : lancer depuis la racine du projet
    token = os.getenv("HF_TOKEN") or sys.exit("HF_TOKEN absent du .env")
    bill_to = os.getenv("HF_BILL_TO")
    client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=token, max_retries=1, timeout=60,
                    default_headers={"X-HF-Bill-To": bill_to} if bill_to else None)
    urls = {p: data_url(p) for p in photos}
    print(f"{len(photos)} photos x {len(models)} modeles, criteres : reconnus >= {FOUND_MIN:.0%}, "
          f"excuses a tort <= {EXCUSED_MAX:.0%}, latence mediane <= {LATENCY_MAX:.0f} s")
    lines = []
    with open(folder / "vlm.jsonl", "a", encoding="utf-8") as log:
        for model in models:
            rows = []
            for p in photos:
                posture = p.stem.rsplit("_", 1)[0]
                try:
                    text, dt = ask(client, model, urls[p])
                    answer = parse(text)
                except Exception as e:  # modele indisponible, quota... : compte comme une mauvaise reponse
                    text, dt, answer = f"erreur : {e}", None, "erreur"
                rows.append((posture, EXPECTED.get(posture, "aucun"), answer, dt))
                log.write(json.dumps({"modele": model, "photo": p.name, "reponse": text, "s": dt}) + "\n")
                print(".", end="", flush=True)
            lines.append(report(model, rows))
    print("\nSynthese (C9a, C9b, C9c) :\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
