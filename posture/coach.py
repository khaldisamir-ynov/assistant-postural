"""Coach : demande 3 conseils a un LLM Hugging Face a partir des statistiques du jour.

Seuls des chiffres agreges sont envoyes (jamais d'image). Le token est celui de l'utilisateur.
"""

import json
import logging
import urllib.error
import urllib.request

from posture import __version__

log = logging.getLogger(__name__)

URL = "https://router.huggingface.co/v1/chat/completions"  # routeur Inference Providers, compatible OpenAI
MODEL = "Qwen/Qwen3.8-27B:cerebras"
TIMEOUT = 30


def summary(stats):
    """Ce qui part chez Hugging Face : des minutes et des compteurs."""
    tracked = stats["good"] + stats["bad"]
    return {
        "minutes_suivies": round(tracked / 60),
        "bonne_posture_pct": round(100 * stats["good"] / tracked) if tracked else None,
        "alertes": stats["alerts"],
        "minutes_epaules_affaissees": round(stats["slouch"] / 60),
        "minutes_tete_en_avant": round(stats["head"] / 60),
        "minutes_penche_sur_le_cote": round(stats["lean"] / 60),
        "minutes_trop_pres_de_l_ecran": round(stats["close"] / 60),
        "minutes_tete_appuyee_sur_la_main": round(stats["hand"] / 60),
        "minutes_posture_affaissee": round(stats["posture"] / 60),
    }


def ask(stats, token, bill_to=""):
    """Retourne le texte du coach. Leve RuntimeError avec un message lisible par l'utilisateur."""
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Tu es un coach en ergonomie de bureau. Reponds en francais, bref et concret."},
            {"role": "user", "content": f"Statistiques de posture de ma journee : {json.dumps(summary(stats))}. "
                                        "Donne-moi 3 conseils courts (une ligne chacun) adaptes a ces chiffres."},
        ],
        "max_tokens": 300,
        "reasoning_effort": "none",  # Qwen3 : sinon la reflexion consomme les tokens et la reponse arrive vide
    }
    # User-Agent explicite : le pare-feu de Hugging Face renvoie 403 a celui de urllib par defaut
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
               "User-Agent": f"assistant-posture/{__version__}"}
    if bill_to:
        headers["X-HF-Bill-To"] = bill_to  # facture l'organisation plutot que le compte perso
    req = urllib.request.Request(URL, json.dumps(body).encode(), headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.load(r)["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        log.warning("Coach : Hugging Face a repondu %s", e.code)
        if e.code in (401, 403):
            raise RuntimeError("Token refusé par Hugging Face (invalide, ou organisation non autorisée).") from e
        if e.code == 402:
            raise RuntimeError("Crédits Hugging Face épuisés.") from e
        raise RuntimeError(f"Hugging Face a répondu une erreur {e.code}. Réessayez plus tard.") from e
    except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
        log.warning("Coach indisponible : %s", e)
        raise RuntimeError("Hugging Face injoignable. Vérifiez la connexion Internet.") from e
