"""Test d'appel au LLM Hugging Face (routeur HF, facture a l'organisation via HF_BILL_TO).

Envoie uniquement des statistiques de posture (des chiffres, jamais d'image) et demande 3 conseils.
Configuration dans .env (voir HUGGING-FACE.md). Usage : .\\.venv\\Scripts\\python mon_script.py
"""
import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".env")  # dossier courant : lancer depuis la racine du projet
token = os.getenv("HF_TOKEN")
if not token:
    sys.exit("HF_TOKEN absent du .env")

bill_to = os.getenv("HF_BILL_TO")
client = OpenAI(base_url=os.getenv("LLM_BASE_URL", "https://router.huggingface.co/v1"), api_key=token,
                default_headers={"X-HF-Bill-To": bill_to} if bill_to else None)

# Exemple de resume de journee, tel que l'assistant pourrait le produire
stats = {
    "temps_devant_ecran_min": 412,
    "bonne_posture_pct": 62,
    "alertes": 14,
    "motif_principal": "tete en avant",
    "motif_secondaire": "epaules affaissees",
    "heure_la_plus_difficile": "15h-16h",
}

debut = time.time()
r = client.chat.completions.create(
    model=os.getenv("LLM_MODEL", "Qwen/Qwen3.8-27B:cerebras"),
    messages=[
        {"role": "system", "content": "Tu es un coach en ergonomie de bureau. Reponds en francais, de facon breve et concrete."},
        {"role": "user", "content": f"Statistiques de posture de ma journee : {stats}. Donne-moi 3 conseils courts (une ligne chacun) pour demain."},
    ],
    max_tokens=300,
    reasoning_effort=os.getenv("LLM_REASONING_EFFORT") or None,
)
print(f"[llm] {r.model} en {time.time() - debut:.1f} s\n")
print(r.choices[0].message.content.strip())
