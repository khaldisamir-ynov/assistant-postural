"""Reperes le long du buste (criteres C13, SPECIFICATIONS.md § 4.8) : la ligne front -> buste raccourcit-elle quand on
n'est pas droit, et seulement alors ?

MediaPipe ne donne aucun point entre epaules et hanches : on pose des reperes virtuels sur le vetement, sous la ligne
des epaules de la photo de reference (droit_0), et on les retrouve sur chaque photo par flux optique (Lucas-Kanade,
aller-retour verifie). Point du haut : le front (milieu des yeux remonte de 0,8 ecart d'yeux). Calcul local.

Usage : .venv\\Scripts\\python essais\\reperes_buste.py essais\\donnees\\A essais\\donnees\\B   (photos, 2 s d'ecart)
Ecrit <dossier>/buste.jpg (reperes dessines, controle a l'oeil).
   ou : .venv\\Scripts\\python essais\\reperes_buste.py essais\\donnees\\C\\landmarks.jsonl   (en continu : reperes
choisis dans le buste a la calibration et suivis image par image par enregistrer.py)
"""
import statistics
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from posture import core  # noqa: E402
from rejouer import BAD_MIN, GOOD_MAX  # noqa: E402

FOREHEAD = 0.8  # ecarts d'yeux au-dessus du milieu des yeux
LK = dict(winSize=(41, 41), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
BACK_MAX = 1.5  # px : ecart aller-retour au-dela duquel un repere est perdu
TRACKED_MIN = 0.5  # moins de la moitie des reperes retrouves : photo non mesuree
BAD, GOOD = ("tete_avant", "avache"), ("droit2", "clavier")
MEASURES = {"a": "front -> buste", "b": "epaules -> buste", "c": "descente du buste"}


def body(lm, w, h):
    """(front, milieu des epaules, largeur des epaules) en pixels, ou None si yeux ou epaules non vus."""
    pts = [lm[i] for i in (core.LEFT_EYE, core.RIGHT_EYE, core.LEFT_SHOULDER, core.RIGHT_SHOULDER)]
    if any(p.visibility < core.MIN_VISIBILITY for p in pts):
        return None
    le, re, ls, rs = (np.array([p.x * w, p.y * h]) for p in pts)
    gap = re - le
    up = np.array([gap[1], -gap[0]])  # perpendiculaire a la ligne des yeux
    up = up if up[1] < 0 else -up      # vers le haut de l'image
    forehead = (le + re) / 2 + FOREHEAD * up
    return forehead, (ls + rs) / 2, abs(ls[0] - rs[0])


def track(ref_gray, gray, pts):
    """Position des reperes sur la nouvelle image et masque des reperes fiables (aller-retour < BACK_MAX px)."""
    p0 = pts.reshape(-1, 1, 2).astype(np.float32)
    p1, ok1, _ = cv2.calcOpticalFlowPyrLK(ref_gray, gray, p0, None, **LK)
    back, ok2, _ = cv2.calcOpticalFlowPyrLK(gray, ref_gray, p1, None, **LK)
    good = (ok1.ravel() == 1) & (ok2.ravel() == 1) & (np.linalg.norm((back - p0).reshape(-1, 2), axis=1) < BACK_MAX)
    return p1.reshape(-1, 2), good


def seed(gray, lm):
    """Reperes poses a la calibration : points faciles a suivre (plis, col, coutures) dans le buste visible,
    sous la ligne des epaules. Tableau N x 2 en pixels (vide si epaules non vues)."""
    h, w = gray.shape
    b = body(lm, w, h)
    if b is None:
        return np.empty((0, 2), np.float32)
    _, (sx, sy), sw = b
    mask = np.zeros_like(gray)
    mask[int(sy + 0.15 * sw):h - 5, int(sx - 0.4 * sw):int(sx + 0.4 * sw)] = 255
    pts = cv2.goodFeaturesToTrack(gray, maxCorners=30, qualityLevel=0.01, minDistance=10, mask=mask)
    return np.empty((0, 2), np.float32) if pts is None else pts.reshape(-1, 2)


def follow(prev_gray, gray, pts):
    """Suivi image par image ; un repere perdu (NaN) n'est jamais retrouve."""
    alive = ~np.isnan(pts[:, 0])
    if alive.any():
        new, good = track(prev_gray, gray, pts[alive])
        pts = pts.copy()
        pts[np.flatnonzero(alive)[~good]] = np.nan
        pts[np.flatnonzero(alive)[good]] = new[good]
    return pts


# Gommettes de couleur vive collees sur le buste (2026-11-13) : retrouvees par leur couleur sur chaque image, rien a
# suivre. Teintes HSV d'OpenCV (0-179) ; orange et jaune evites, trop proches de la peau et du bois
COLORS = {"vert": ((35, 80, 60), (85, 255, 255)), "rose": ((140, 80, 80), (175, 255, 255)),
          "bleu": ((95, 120, 60), (130, 255, 255))}


def stickers(frame, lm, color):
    """Centres des gommettes (pixels, du haut vers le bas) dans la zone du buste, sous la ligne des epaules."""
    h, w = frame.shape[:2]
    b = body(lm, w, h)
    if b is None:
        return []
    _, (sx, sy), sw = b
    x0, x1, y0 = max(0, int(sx - 0.6 * sw)), min(w, int(sx + 0.6 * sw)), max(0, int(sy - 0.1 * sw))
    hsv = cv2.cvtColor(frame[y0:, x0:x1], cv2.COLOR_BGR2HSV)
    mask = cv2.morphologyEx(cv2.inRange(hsv, *COLORS[color]), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, _, stats, centers = cv2.connectedComponentsWithStats(mask)
    blobs = [(stats[i, cv2.CC_STAT_AREA], centers[i]) for i in range(1, n)
             if stats[i, cv2.CC_STAT_AREA] >= (0.025 * sw) ** 2]  # gommette d'environ 2 cm, epaules d'environ 40
    keep = sorted(blobs, key=lambda b: -b[0])[:5]
    return sorted(([float(c[0] + x0), float(c[1] + y0)] for _, c in keep), key=lambda c: c[1])


def measures(ref, cur, ref_pts, pts, mask):
    """Ecarts a la reference (a, b, c) sur les seuls reperes retrouves. ref, cur : sorties de body()."""
    (rf, rs, rw), (f, s, w) = ref, cur
    mean = lambda origin, p: np.linalg.norm(p[mask] - origin, axis=1).mean()  # noqa: E731
    return {"a": 1 - (mean(f, pts) / w) / (mean(rf, ref_pts) / rw),
            "b": 1 - (mean(s, pts) / w) / (mean(rs, ref_pts) / rw),
            "c": (pts[mask][:, 1].mean() - ref_pts[mask][:, 1].mean()) / rw}


def threshold(values):
    """Seuil C13a : {posture: [valeurs ou None]} de tous les dossiers -> (seuil, marge) ; marge <= 0 = pas de seuil."""
    lo = max(sorted((v or 0 for v in values[p]), reverse=True)[int(GOOD_MAX * len(values[p]))] for p in GOOD)
    hi = min(sorted(v or 0 for v in values[p])[int((1 - BAD_MIN) * len(values[p]))] for p in BAD)
    return (lo + hi) / 2, hi - lo


def analyse(folder, pose):
    photos = sorted((folder / "photos").glob("*.jpg"))
    imgs = {p.stem: cv2.imread(str(p)) for p in photos}
    h, w = imgs["droit_0"].shape[:2]
    lms = {k: pose.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)).pose_landmarks for k, im in imgs.items()}
    ref = body(lms["droit_0"].landmark, w, h)
    ref_gray = cv2.cvtColor(imgs["droit_0"], cv2.COLOR_BGR2GRAY)
    # 2026-11-13 : memes reperes que l'essai en continu (plis, col) ; la 1re version (grille fixe sur un t-shirt uni)
    # n'en retrouvait que 14 photos sur 34
    ref_pts = seed(ref_gray, lms["droit_0"].landmark)
    out, tiles = {}, []
    for k, im in imgs.items():
        if k == "droit_0":
            continue
        cur = body(lms[k].landmark, w, h) if lms[k] else None
        pts, mask = track(ref_gray, cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), ref_pts)
        ok = cur is not None and mask.mean() >= TRACKED_MIN
        out[k] = measures(ref, cur, ref_pts, pts, mask) if ok else None
        if k.endswith("_3"):  # une photo par posture sur la planche
            t = im.copy()
            for p, g in zip(pts, mask):
                cv2.circle(t, tuple(int(v) for v in p), 6, (0, 255, 0) if g else (0, 0, 255), -1)
            if cur:
                cv2.circle(t, tuple(int(v) for v in cur[0]), 8, (255, 0, 255), -1)
            cv2.putText(t, k, (10, 30), 0, 1, (0, 255, 255), 2)
            tiles.append(cv2.resize(t, (320, 240)))
    tiles += [np.zeros_like(tiles[0])] * (-len(tiles) % 5)
    cv2.imwrite(str(folder / "buste.jpg"), np.vstack([np.hstack(tiles[i:i + 5]) for i in range(0, len(tiles), 5)]))
    print(f"{folder} : {len(ref_pts)} reperes poses, planche {folder / 'buste.jpg'}")
    return out, len(ref_pts)


def continuous(files):
    """Essai en continu sur des enregistrements avec reperes suivis image par image (enregistrer.py, champ « buste »)."""
    import json
    from collections import deque

    from rejouer import CALIBRATION, landmarks
    from scanner_paires import quantile
    values = {k: [] for k in MEASURES}  # par mesure : un dict {posture: [valeurs]} par enregistrement
    tracked_good = []
    for path in files:
        rows = [r for r in map(json.loads, open(path, encoding="utf-8")) if r.get("buste") or "gommettes" in r]
        if not rows:
            sys.exit(f"{path} : pas de reperes du buste (enregistrement anterieur au 2026-11-13 ?)")
        field = "gommettes" if "gommettes" in rows[0] else "buste"
        # Gommettes : leur nombre pendant la calibration ; une image ou on n'en voit pas autant n'est pas mesuree
        count = statistics.mode(len(r["gommettes"]) for r in rows if r["posture"] == "droit") \
            if field == "gommettes" else None

        def parse(r):
            w, h = r["wh"]
            if field == "gommettes":
                pts = r["gommettes"] if len(r["gommettes"]) == count else [None] * count
            else:
                pts = r["buste"]
            return body(landmarks(r), w, h), np.array([p or [np.nan, np.nan] for p in pts], float)
        calib = [parse(r) for r in rows if r["posture"] == "droit" and CALIBRATION[0] <= r["t"] < CALIBRATION[1]]
        calib = [(b, p) for b, p in calib if b]
        ref = tuple(np.median([b[i] for b, _ in calib], axis=0) for i in range(3))
        ref_pts = np.nanmedian([p for _, p in calib], axis=0)
        per = {k: {} for k in MEASURES}
        for posture in dict.fromkeys(r["posture"] for r in rows):
            recent = deque(maxlen=10)  # meme lissage que detector._loop
            for r in rows:
                if r["posture"] != posture:
                    continue
                cur, pts = parse(r)
                mask = ~np.isnan(pts[:, 0]) & ~np.isnan(ref_pts[:, 0])
                m = measures(ref, cur, ref_pts, pts, mask) if cur and mask.sum() >= min(3, len(mask)) else None
                recent.append(m) if m else recent.clear()
                for k in MEASURES:
                    per[k].setdefault(posture, []).append(
                        statistics.mean(x[k] for x in recent) if recent else None)
                if posture in ("droit", "droit2", "clavier"):
                    tracked_good.append(m is not None)
        if field == "gommettes":
            seen = sum(len(r["gommettes"]) == count for r in rows) / len(rows)
            print(f"{path} : {count} gommettes, toutes vues sur {seen:.0%} des images")
        else:
            alive = [sum(p is not None for p in r["buste"]) for r in rows]
            print(f"{path} : {len(rows[0]['buste'])} reperes poses, {alive[-1]} encore suivis a la fin")
        for k in MEASURES:
            values[k].append(per[k])
    for k, name in MEASURES.items():
        print(f"\n== ({k}) {name} : mediane par posture ==")
        postures = list(values[k][0])
        print(f"{'posture':12}" + "".join(f"{Path(f).parent.name[-10:]:>12}" for f in files))
        for p in postures:
            print(f"{p:12}" + "".join(
                f"{statistics.median(v for v in d.get(p, []) if v is not None):+12.3f}"
                if any(v is not None for v in d.get(p, [])) else f"{'-':>12}" for d in values[k]))
        lo = max(quantile(d[p], 1 - GOOD_MAX) for d in values[k] for p in GOOD)
        hi = min(quantile(d[p], 1 - BAD_MIN) for d in values[k] for p in BAD)
        seuil = (lo + hi) / 2
        noise = max(statistics.pstdev([v for v in d["droit"] if v is not None]) for d in values[k])
        ok = {"C13a": hi > lo, "C13b": hi > lo and noise < seuil / 3,
              "C13c": sum(tracked_good) / len(tracked_good) >= 0.8}
        print(f"seuil {seuil:+.3f}, marge {hi - lo:+.3f}, bruit {noise:.3f}, images suivies (bonnes postures) "
              f"{sum(tracked_good) / len(tracked_good):.0%} -> " + ", ".join(
                  f"{c} {'OK' if v else 'non'}" for c, v in ok.items()))


def main():
    if sys.argv[1:] and all(a.endswith(".jsonl") for a in sys.argv[1:]):
        return continuous(sys.argv[1:])
    folders = [Path(a) for a in sys.argv[1:]]
    if not folders:
        sys.exit(__doc__)
    with mp.solutions.pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
        results = {f: analyse(f, pose)[0] for f in folders}
    postures = ["droit", "droit2", "clavier", "tete_avant", "avache", "penche", "menton_main", "trop_pres",
                "telephone", "boire"]
    for key, name in MEASURES.items():
        print(f"\n== ({key}) {name} : mediane par posture (photos non mesurees entre parentheses) ==")
        print(f"{'posture':12}" + "".join(f"{f.name[-10:]:>16}" for f in folders))
        by = {p: [] for p in postures}
        for p in postures:
            cells = []
            for f in folders:
                vals = [m[key] if m else None for k, m in results[f].items() if k.rsplit("_", 1)[0] == p]
                by[p] += vals
                got = [v for v in vals if v is not None]
                cells.append(f"{statistics.median(got):+.3f} ({len(vals) - len(got)})" if got else "-")
            print(f"{p:12}" + "".join(f"{c:>16}" for c in cells))
        # C13a dans chaque dossier, au meme seuil : marge commune = min des bornes hautes - max des basses
        per = [threshold({p: [m[key] if m else None for k, m in results[f].items() if k.rsplit("_", 1)[0] == p]
                          for p in BAD + GOOD}) for f in folders]
        lo = max(t - mg / 2 for t, mg in per)
        hi = min(t + mg / 2 for t, mg in per)
        seuil = (lo + hi) / 2
        noise = max(statistics.pstdev([m[key] for k, m in results[f].items() if k.startswith("droit_") and m])
                    for f in folders)
        tracked = [m is not None for f in folders for k, m in results[f].items()
                   if k.rsplit("_", 1)[0] in ("droit", "droit2", "clavier")]
        c13 = {"C13a": hi > lo, "C13b": hi > lo and noise < seuil / 3, "C13c": sum(tracked) / len(tracked) >= 0.8}
        print(f"seuil {seuil:+.3f}, marge {hi - lo:+.3f}, bruit {noise:.3f}, suivis {sum(tracked)}/{len(tracked)} -> "
              + ", ".join(f"{k} {'OK' if v else 'non'}" for k, v in c13.items()))


if __name__ == "__main__":
    main()
