from posture.core import compute_metrics


def metrics(l_ear, r_ear, l_sh, r_sh, eye_drop=0.0):
    """Metriques d'une posture simulee : yeux places entre les oreilles, un peu plus haut (symetrique, donc
    identique avec ou sans miroir). eye_drop baisse les yeux seuls, comme une tete qui s'incline."""
    def eye(ear, other):
        return ear[0] + 0.3 * (other[0] - ear[0]), ear[1] - 0.03 + eye_drop
    return compute_metrics(l_ear, r_ear, l_sh, r_sh, eye(l_ear, r_ear), eye(r_ear, l_ear))
