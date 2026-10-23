"""Logique de posture, pure et testable sans webcam.

Principe (webcam de face) :
    - Avachissement : les epaules descendent dans l'image par rapport a la calibration.
    - Tete en avant : la distance verticale oreilles -> epaules se reduit (le cou "rentre").
Toutes les mesures sont divisees par la largeur des epaules pour ne pas dependre de la distance a la camera.
"""

# Valeurs validees en usage reel (2026-10-23) : seuils serres, le delai filtre les mouvements brefs
ALERT_DELAY_SECONDS = 2.0   # mauvaise posture toleree avant alerte
SLOUCH_THRESHOLD = 0.03     # descente des epaules, en fraction de largeur d'epaules
HEAD_THRESHOLD = 0.05       # baisse relative du ratio oreilles/epaules
MIN_VISIBILITY = 0.5        # en dessous, le repere est considere hors champ

# Index des reperes MediaPipe Pose
LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER = 7, 8, 11, 12


def compute_metrics(l_ear, r_ear, l_sh, r_sh):
    """Retourne (hauteur des epaules, ratio oreilles->epaules, largeur d'epaules).

    Points en coordonnees normalisees (x, y), y vers le bas. Milieux et valeurs absolues :
    le resultat est identique avec ou sans effet miroir.
    """
    shoulder_y = (l_sh[1] + r_sh[1]) / 2
    ear_y = (l_ear[1] + r_ear[1]) / 2
    width = abs(l_sh[0] - r_sh[0])
    return shoulder_y, (shoulder_y - ear_y) / width, width


def deviations(current, reference):
    """Ecarts a la reference : (descente des epaules en largeurs d'epaules, baisse relative du ratio de la tete)."""
    shoulder_y, head_ratio, _ = current
    ref_shoulder_y, ref_head_ratio, ref_width = reference
    return (shoulder_y - ref_shoulder_y) / ref_width, 1 - head_ratio / ref_head_ratio


def evaluate_posture(current, reference, slouch_threshold=SLOUCH_THRESHOLD, head_threshold=HEAD_THRESHOLD):
    """Retourne (slouching, head_forward)."""
    slouch_dev, head_dev = deviations(current, reference)
    return slouch_dev > slouch_threshold, head_dev > head_threshold


def valid_reference(ref):
    """Une reference exploitable : 3 nombres, tete au-dessus des epaules, largeur non nulle."""
    return (isinstance(ref, (list, tuple)) and len(ref) == 3
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in ref)
            and ref[1] > 0 and ref[2] > 0)


def extract_metrics(landmarks):
    """Metriques depuis les landmarks MediaPipe, ou None si oreilles/epaules hors champ."""
    pts = [landmarks[i] for i in (LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER)]
    if any(p.visibility < MIN_VISIBILITY for p in pts):
        return None
    metrics = compute_metrics(*[(p.x, p.y) for p in pts])
    return metrics if metrics[2] > 0.01 else None  # epaules confondues = vue de profil, inexploitable
