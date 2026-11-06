"""Logique de posture, pure et testable sans webcam.

Principe (webcam de face) :
    - Etape 1, posture affaissee : la hauteur haut de la tete -> epaules se raccourcit quand on s'avachit ou qu'on
      avance la tete. Rapport de deux longueurs du corps : peu sensible a la position de la camera.
    - Avachissement : les epaules descendent dans l'image par rapport a la calibration.
    - Tete en avant : la distance verticale oreilles -> epaules se reduit (le cou "rentre").
    - Etape 2, penche sur le cote / accoude : l'axe du cou (milieu des oreilles -> milieu des epaules) s'incline.
    - Trop pres de l'ecran : les epaules paraissent plus larges qu'a la calibration.
    - Tete appuyee sur la main : une main est tout pres du visage (sans reference : mesure absolue).
Toutes les mesures sont divisees par la largeur des epaules pour ne pas dependre de la distance a la camera.
"""

import math

# Valeurs validees en usage reel (2026-10-23) : seuils serres, le delai filtre les mouvements brefs
ALERT_DELAY_SECONDS = 2.0   # mauvaise posture toleree avant alerte
# Banc d'essai du 2026-10-30 (essais/rejouer.py) : a 3 %, aucune alerte en posture droite ni au clavier, tete en avant
# 100 % et avachi 98 % des images ; a 4 %, l'avachi tombe a 61 %
POSTURE_THRESHOLD = 0.03    # etape 1 : raccourcissement de la hauteur tete-epaules
SLOUCH_THRESHOLD = 0.05     # descente des epaules (largeurs d epaules) ; a 3 %, la derive naturelle assis droit declenche deja
HEAD_THRESHOLD = 0.05       # baisse relative du ratio oreilles/epaules
# Essai du 2026-10-30 (10 postures) : axe du cou penche de 12,3 degres contre 2,3 au plus sinon (pente des epaules :
# marge 2,9x seulement) ; ordinateur deplace : 2,7 degres au plus
LEAN_ANGLE = 6.0            # etape 2 : inclinaison laterale de l'axe du cou, en degres
# Essai du 2026-10-30 : trop pres +73 % contre +10 % au plus
CLOSE_THRESHOLD = 0.25      # elargissement apparent des epaules
HAND_THRESHOLD = 2.0        # main a moins de 2 ecarts d'yeux du nez (essai : menton dans la main 1.4, sinon 2.4 et plus)
MIN_VISIBILITY = 0.5        # en dessous, le repere est considere hors champ
TOP_OF_HEAD = 1.5           # haut de la tete estime a 1,5 ecart d'yeux au-dessus des yeux (MediaPipe ne le fournit pas)

# Index des reperes MediaPipe Pose
NOSE, LEFT_EYE, RIGHT_EYE = 0, 2, 5
LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER = 7, 8, 11, 12
HAND_POINTS = range(15, 21)  # poignets, auriculaires, index


def compute_metrics(l_ear, r_ear, l_sh, r_sh, l_eye, r_eye):
    """Retourne (hauteur des epaules, ratio oreilles->epaules, largeur d'epaules, angle du cou en degres,
    hauteur haut de la tete -> epaules en largeurs d'epaules).

    Points en coordonnees normalisees (x, y), y vers le bas. L'angle est signe mais toujours compare a la
    calibration, faite dans les memes conditions (miroir compris).
    """
    shoulder_y = (l_sh[1] + r_sh[1]) / 2
    ear_y = (l_ear[1] + r_ear[1]) / 2
    width = abs(l_sh[0] - r_sh[0])
    eye_gap = ((l_eye[0] - r_eye[0]) ** 2 + (l_eye[1] - r_eye[1]) ** 2) ** 0.5
    top_y = (l_eye[1] + r_eye[1]) / 2 - TOP_OF_HEAD * eye_gap
    neck = math.degrees(math.atan2((l_ear[0] + r_ear[0]) / 2 - (l_sh[0] + r_sh[0]) / 2, shoulder_y - ear_y))
    return shoulder_y, (shoulder_y - ear_y) / width, width, neck, (shoulder_y - top_y) / width


def deviations(current, reference):
    """Ecarts a la reference : (descente des epaules en largeurs d'epaules, baisse relative du ratio de la tete,
    inclinaison du cou en degres, elargissement relatif des epaules, raccourcissement de la hauteur tete-epaules).

    Reference d'une version precedente (moins de 5 nombres) : mesures absentes, ecarts nuls.
    """
    shoulder_y, head_ratio, width, neck, height = current
    ref_shoulder_y, ref_head_ratio, ref_width = reference[:3]
    lean_dev = abs(neck - reference[3]) if len(reference) > 4 else 0.0  # avant l'etape 1, l'indice 3 etait une pente
    shortening = 1 - height / reference[4] if len(reference) > 4 else 0.0
    return ((shoulder_y - ref_shoulder_y) / ref_width, 1 - head_ratio / ref_head_ratio, lean_dev,
            width / ref_width - 1, shortening)


def evaluate_posture(current, reference, slouch_threshold=SLOUCH_THRESHOLD, head_threshold=HEAD_THRESHOLD):
    """Retourne (slouching, head_forward)."""
    slouch_dev, head_dev, _, _, _ = deviations(current, reference)
    return slouch_dev > slouch_threshold, head_dev > head_threshold


def valid_reference(ref):
    """Une reference exploitable : 3 a 5 nombres, tete au-dessus des epaules, largeur et hauteur non nulles."""
    return (isinstance(ref, (list, tuple)) and len(ref) in (3, 4, 5)
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in ref)
            and ref[1] > 0 and ref[2] > 0 and (len(ref) < 5 or ref[4] > 0))


def extract_metrics(landmarks):
    """Metriques depuis les landmarks MediaPipe, ou None si oreilles, epaules ou yeux hors champ."""
    pts = [landmarks[i] for i in (LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_EYE, RIGHT_EYE)]
    if any(p.visibility < MIN_VISIBILITY for p in pts):
        return None
    metrics = compute_metrics(*[(p.x, p.y) for p in pts])
    return metrics if metrics[2] > 0.01 else None  # epaules confondues = vue de profil, inexploitable


def hand_face_distance(landmarks):
    """Distance de la main la plus proche au nez, en ecarts d'yeux (independant de la distance a la camera).

    None si le visage ou aucune main n'est visible.
    """
    face = [landmarks[i] for i in (NOSE, LEFT_EYE, RIGHT_EYE)]
    hands = [landmarks[i] for i in HAND_POINTS if landmarks[i].visibility >= MIN_VISIBILITY]
    eyes = ((face[1].x - face[2].x) ** 2 + (face[1].y - face[2].y) ** 2) ** 0.5
    if not hands or eyes < 0.005 or any(p.visibility < MIN_VISIBILITY for p in face):
        return None
    nose = face[0]
    return min(((p.x - nose.x) ** 2 + (p.y - nose.y) ** 2) ** 0.5 for p in hands) / eyes
