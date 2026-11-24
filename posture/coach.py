"""Coach : rapport de journee et conseils, a partir des statistiques du jour (totaux, deroule par demi-heure) et des
jours precedents.

Par defaut, local_report() le calcule sur le poste (regles et table de conseils, criteres C16). En option, ask() le
fait rediger par un LLM Hugging Face : seuls des chiffres agreges sont envoyes (jamais d'image), avec le token de
l'utilisateur.
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


# Titres « ## » et puces « - » : la page les met en forme, sans jamais interpreter de HTML venant du LLM
REPORT_FORMAT = ("« ## Bilan » (2 phrases : la journee en chiffres, comparee aux jours precedents s'il y en a), "
                 "« ## Postures a surveiller » (une puce « - » par mauvaise posture notable, avec sa duree), "
                 "« ## Moments de la journee » (puces : heures ou la posture se degrade ou est bonne), "
                 "« ## Conseils » (3 puces courtes et concretes, adaptees a ces chiffres). "
                 "Pas d'autre mise en forme, pas de gras.")

SLOT_MIN_SECONDS = 5 * 60  # demi-heure suivie moins de 5 min : pourcentage trop incertain pour etre envoye


def summary(stats, days=()):
    """Ce qui part chez Hugging Face : des minutes, des pourcentages et des compteurs. days : stats.last_days()."""
    tracked = stats["good"] + stats["bad"]
    return {
        "minutes_suivies": round(tracked / 60),
        "bonne_posture_pct": round(100 * stats["good"] / tracked) if tracked else None,
        "alertes": stats["alerts"],
        "minutes_tete_en_avant": round(stats["head"] / 60),
        "minutes_penche_sur_le_cote": round(stats["lean"] / 60),
        "minutes_trop_pres_de_l_ecran": round(stats["close"] / 60),
        "minutes_tete_appuyee_sur_la_main": round(stats["hand"] / 60),
        "minutes_posture_affaissee": round(stats["posture"] / 60),
        "minutes_buste_affaisse": round(stats["axis"] / 60),
        "par_demi_heure": [{"debut": slot, "minutes_suivies": round((g + b) / 60),
                            "bonne_posture_pct": round(100 * g / (g + b))}
                           for slot, (g, b) in sorted(stats.get("slots", {}).items()) if g + b >= SLOT_MIN_SECONDS],
        "jours_precedents": [{"date": d["date"], "minutes_suivies": d["minutes"], "bonne_posture_pct": d["good_pct"],
                              "alertes": d["alerts"]} for d in days if d["date"] != stats["date"]],
    }


LABELS = {"posture": "Posture affaissée", "head": "Tête en avant", "lean": "Penché sur le côté",
          "close": "Trop près de l'écran", "hand": "Tête appuyée sur la main", "axis": "Buste affaissé"}
# shortcut: conseils rediges le 2026-11-20 sans source citee ; a relire par l'utilisateur (C16e) et a sourcer
# (ex. fiches INRS) avant de les presenter comme des recommandations
ADVICE = {
    "posture": ("Reculez le bassin au fond du siège et appuyez le bas du dos contre le dossier.",
                "Placez le haut de l'écran à hauteur des yeux, ou un peu en dessous, pour ne pas vous tasser."),
    "head": ("Rapprochez l'écran plutôt que d'avancer la tête vers lui.",
             "Si vous plissez les yeux pour lire, agrandissez le texte (Ctrl +) au lieu de vous pencher."),
    "lean": ("Gardez les deux avant-bras posés à la même hauteur, sur le bureau ou les accoudoirs.",
             "Placez ce que vous regardez souvent (document, 2e écran) face à vous plutôt que sur le côté."),
    "close": ("Reculez le siège ou l'écran : environ une longueur de bras entre vos yeux et l'écran.",
              "Si vous plissez les yeux pour lire, agrandissez le texte (Ctrl +) au lieu de vous pencher."),
    "hand": ("Quand vous réfléchissez, posez les mains sur le bureau plutôt que sous le menton.",
             "Si la tête vous semble lourde, c'est le moment d'une courte pause debout."),
    "axis": ("Reculez le bassin au fond du siège et appuyez le bas du dos contre le dossier.",
             "Levez-vous quelques minutes : le buste se tasse souvent après une longue période assise."),
}
GENERAL = ("Levez-vous et marchez quelques minutes toutes les heures.",
           "Recalibrez après un changement de siège, d'écran ou de lieu, pour que les alertes restent justes.",
           "Au retour d'une pause, prenez trois secondes pour vous rasseoir droit avant de reprendre.")
# Conseils declenches par les chiffres du jour (C16e), completes par les valeurs du jour
PAUSE = "Votre posture se dégrade vers {debut} : prévoyez une pause juste avant."
STREAK = ("De {debut} à {fin}, vous avez travaillé {duree} presque sans pause : levez-vous quelques minutes au moins "
          "une fois par heure.")
ALERTS = ("Environ {n} alertes par heure : si beaucoup vous semblent injustifiées, recalibrez ou augmentez la "
          "tolérance dans Réglages → Détection.")
GOOD_DAY = "Très bonne journée : gardez la même installation (siège, écran) et le même rythme de pauses."
COMPARABLE = 3  # points de % : en dessous, la journee est « comparable » aux precedentes (C16b)
STREAK_SLOT_SECONDS = 28 * 60  # demi-heure « sans pause » : moins de 2 min hors du champ
STREAK_SLOTS = 4               # 2 h d'affilee
ALERTS_PER_HOUR = 6            # une alerte toutes les 10 min, sur au moins 30 min suivies
GOOD_PCT = 90
MAX_TIPS = 5


def _duration(minutes):
    if not minutes:
        return "moins d'une minute"
    return f"{minutes // 60} h {minutes % 60:02d}" if minutes >= 60 else f"{minutes} min"


def _minutes(slot):
    h, m = map(int, slot.split(":"))
    return h * 60 + m


def _clock(minutes):
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def _slot_end(start):
    return f"{start}-{_clock(_minutes(start) + 30)}"


def _longest_streak(slots):
    """Plus longue suite de demi-heures presque entierement suivies : (debut, nombre). A egalite, la plus tot."""
    best, run, prev = (None, 0), (None, 0), None
    for slot, (g, b) in sorted(slots.items()):
        if g + b < STREAK_SLOT_SECONDS:
            prev = None
            continue
        run = (run[0], run[1] + 1) if prev is not None and _minutes(slot) - prev == 30 else (slot, 1)
        prev = _minutes(slot)
        best = max(best, run, key=lambda r: r[1])
    return best


def local_report(stats, days=()):
    """Rapport de journee calcule sur le poste (criteres C16), au format du LLM : titres « ## », puces « - »."""
    s = summary(stats, days)  # memes chiffres que ceux qu'on enverrait au LLM
    lines = ["## Bilan", f"Temps suivi aujourd'hui : {_duration(s['minutes_suivies'])}, dont {s['bonne_posture_pct']} % "
                         f"en bonne posture ; {s['alertes']} alerte{'s' if s['alertes'] > 1 else ''}."]
    tracked, before, gap = stats["good"] + stats["bad"], s["jours_precedents"], 0
    if tracked < SLOT_MIN_SECONDS:  # meme regle que pour les demi-heures : pourcentage trop incertain
        lines.append("Moins de 5 minutes suivies : trop peu pour comparer avec les jours précédents.")
    elif before:
        mean = round(sum(d["bonne_posture_pct"] for d in before) / len(before))
        gap = s["bonne_posture_pct"] - mean
        verdict = "mieux que" if gap >= COMPARABLE else "moins bien que" if gap <= -COMPARABLE else "comparable à"
        others = (f"votre jour précédent ({mean} %)" if len(before) == 1
                  else f"vos {len(before)} jours précédents ({mean} % en moyenne)")
        lines.append(f"C'est {verdict} {others}.")
    else:
        lines.append("Pas encore de jour précédent pour comparer.")

    bad = sorted((k for k in LABELS if stats[k] >= 60), key=lambda k: -stats[k])  # tri stable : egalite = ordre fixe
    lines.append("## Postures à surveiller")
    lines += [f"- {LABELS[k]} : {_duration(round(stats[k] / 60))} ({round(100 * stats[k] / tracked)} % du temps suivi)"
              for k in bad] or ["- Aucune mauvaise posture d'au moins une minute."]

    slots = s["par_demi_heure"]
    lines.append("## Moments de la journée")
    worst = None
    if len(slots) >= 2:
        best = max(slots, key=lambda x: x["bonne_posture_pct"])  # max et min gardent le 1er : a egalite, le plus tot
        worst = min(slots, key=lambda x: x["bonne_posture_pct"])
        lines += [f"- Meilleur moment : {_slot_end(best['debut'])}, {best['bonne_posture_pct']} % en bonne posture.",
                  f"- Moment le plus difficile : {_slot_end(worst['debut'])}, {worst['bonne_posture_pct']} % en bonne posture."]
    elif slots:
        lines.append(f"- Une seule demi-heure suivie assez longtemps : {_slot_end(slots[0]['debut'])}, "
                     f"{slots[0]['bonne_posture_pct']} % en bonne posture.")
    else:
        lines.append("- Pas encore de demi-heure suivie au moins 5 minutes.")

    # Par ordre de priorite : au-dela de MAX_TIPS, les derniers sautent
    tips = [ADVICE[k][0] for k in bad[:1]]
    start, count = _longest_streak(stats.get("slots", {}))
    if count >= STREAK_SLOTS:
        tips.append(STREAK.format(debut=start, fin=_clock(_minutes(start) + 30 * count), duree=_duration(30 * count)))
    if worst and worst["bonne_posture_pct"] < 100:
        tips.append(PAUSE.format(debut=worst["debut"]))
    tips += [ADVICE[k][0] for k in bad[1:3]]
    if tracked >= 30 * 60 and stats["alerts"] * 3600 / tracked >= ALERTS_PER_HOUR:
        tips.append(ALERTS.format(n=round(stats["alerts"] * 3600 / tracked)))
    if gap <= -COMPARABLE:  # moins bien que d'habitude : l'installation a peut-etre change
        tips.append(GENERAL[1])
    tips += [ADVICE[k][1] for k in bad[:1]]
    if not bad and tracked >= SLOT_MIN_SECONDS and s["bonne_posture_pct"] >= GOOD_PCT:
        tips.insert(0, GOOD_DAY)
    tips = list(dict.fromkeys(tips))  # sans doublon, dans l'ordre
    general = [g for g in GENERAL if not (count >= STREAK_SLOTS and g == GENERAL[0])]  # deja dit par STREAK
    lines.append("## Conseils")
    lines += [f"- {tip}" for tip in list(dict.fromkeys(tips + general))[:max(3, min(MAX_TIPS, len(tips)))]]
    return "\n".join(lines)


def ask(stats, token, bill_to="", days=()):
    """Retourne le texte du coach. Leve RuntimeError avec un message lisible par l'utilisateur."""
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Tu es un coach en ergonomie de bureau. Reponds en francais, bref et concret."},
            {"role": "user", "content": f"Statistiques de posture de ma journee : {json.dumps(summary(stats, days))}. "
                                        f"Redige mon rapport de journee avec exactement ces titres : {REPORT_FORMAT}"},
        ],
        "max_tokens": 700,
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
