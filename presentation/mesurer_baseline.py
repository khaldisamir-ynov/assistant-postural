"""Fiche de performance du cours (presentation/diagnostiquer_performances.ipynb, § 12).

Le modèle du projet est MediaPipe Pose 0.10.21, pas ResNet-18. L'application traite une image
webcam à la fois, sur le processeur : il n'y a pas de lot tensoriel. Un « lot » de N est donc
N images passées l'une après l'autre. L'image est une personne générée (essais/donnees/genere) :
sur des pixels aléatoires, MediaPipe ne trouve personne et ne lance que son détecteur, ce qui
n'est pas le chemin de l'application. Deux chemins sont mesurés : « suivi » (l'application, image
après image) et « premiere_image » (détecteur puis repères, quand la personne vient d'apparaître).

Usage : .venv\\Scripts\\python presentation\\mesurer_baseline.py
Écrit baseline_performance.csv et baseline_throughput.csv dans ce dossier.
"""
import ctypes
import platform
import statistics
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from posture import core  # noqa: E402

OUT = Path(__file__).resolve().parent
WARMUP, REPS, THROUGH_REPS = 10, 50, 30
LOTS = (1, 2, 4, 8, 16)
# taille laissée par OpenCV quand l'application ne règle pas la webcam
FRAME = (480, 640, 3)
# Personne générée (jeu C10, exclu de git) : une vraie silhouette, sans filmer personne
PHOTO = Path(__file__).resolve().parent.parent / "essais" / "donnees" / "genere" / "photos" / "droit_0.jpg"


def rss_mib():
    """Mémoire de travail du processus (Mo). Inclut Python, pas seulement le réseau."""
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong),
                    ("peak_ws", ctypes.c_size_t), ("ws", ctypes.c_size_t),
                    *[(f"pad{i}", ctypes.c_size_t) for i in range(6)]]

    kernel, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    kernel.GetCurrentProcess.restype = ctypes.c_void_p  # un handle tronqué sur 32 bits vaut 0
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    c = Counters(cb=ctypes.sizeof(Counters))
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(c), c.cb):
        raise OSError("GetProcessMemoryInfo a échoué")
    return c.ws / 1024 ** 2, c.peak_ws / 1024 ** 2


def model_files():
    """Les deux réseaux réellement chargés : complexité 1, celle de l'application."""
    root = Path(mp.__file__).resolve().parent
    return [root / "modules/pose_detection/pose_detection.tflite",
            root / "modules/pose_landmark/pose_landmark_full.tflite"]


def percentile(samples, q):
    s = sorted(samples)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def latencies(pose, rgb):
    """Chauffe, puis REPS mesures de pose.process sur la meme image."""
    for _ in range(WARMUP):
        pose.process(rgb)
    samples = []
    for _ in range(REPS):
        t = time.perf_counter()
        pose.process(rgb)
        samples.append((time.perf_counter() - t) * 1000)
    return samples


def main():
    if not PHOTO.exists():
        sys.exit(f"Photo absente : {PHOTO} (jeu genere, voir essais/generer_images.py)")
    bgr = cv2.resize(cv2.imread(str(PHOTO)), (FRAME[1], FRAME[0]))

    def preprocess(image):
        return cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)

    rgb = preprocess(bgr)
    # Suivi : le chemin de l'application, une fois la personne trouvee (reseau des reperes seul, sur la zone suivie)
    pose = mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    found = pose.process(rgb)
    # Sans personne (pixels aleatoires de la 1re fiche), seul le detecteur tourne : ce n'est pas le cout reel
    assert found.pose_landmarks, "MediaPipe ne voit personne sur la photo : la mesure serait celle du detecteur seul"
    paths = {"suivi": latencies(pose, rgb)}
    # Premiere image (ou personne perdue) : detecteur puis reperes, a chaque appel
    with mp.solutions.pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as first:
        paths["premiere_image"] = latencies(first, rgb)

    pre = []
    for _ in range(100):
        t = time.perf_counter()
        preprocess(bgr)
        pre.append((time.perf_counter() - t) * 1000)
    post = []
    for _ in range(100):
        t = time.perf_counter()
        core.extract_metrics(found.pose_landmarks.landmark)
        post.append((time.perf_counter() - t) * 1000)

    rows = []
    for n in LOTS:
        for _ in range(WARMUP):
            for _ in range(n):
                pose.process(rgb)
        t = time.perf_counter()
        for _ in range(THROUGH_REPS):
            for _ in range(n):
                pose.process(rgb)
        elapsed = time.perf_counter() - t
        images = n * THROUGH_REPS
        rows.append((n, elapsed, images, images / elapsed, elapsed * 1000 / THROUGH_REPS))

    ws, peak = rss_mib()
    pose.close()
    files = model_files()
    weight = sum(p.stat().st_size for p in files) / 1024 ** 2

    cpu = (platform.processor() or platform.machine()).replace(",", "")
    perf = OUT / "baseline_performance.csv"
    thru = OUT / "baseline_throughput.csv"
    perf.write_text(
        "modele,chemin,materiel,python,image,latence_moyenne_ms,latence_mediane_ms,p95_ms,p99_ms,"
        "pretraitement_median_ms,posttraitement_median_ms,poids_fichiers_mib,rss_mo,rss_pic_mo\n"
        + "".join(
            f"mediapipe-pose-0.10.21,{name},{cpu},{platform.python_version()},{FRAME[1]}x{FRAME[0]},"
            f"{statistics.mean(s):.2f},{statistics.median(s):.2f},{percentile(s, 0.95):.2f},{percentile(s, 0.99):.2f},"
            f"{statistics.median(pre):.3f},{statistics.median(post):.3f},{weight:.2f},{ws:.0f},{peak:.0f}\n"
            for name, s in paths.items()),
        encoding="utf-8")
    thru.write_text(
        "lot,duree_s,images,images_par_s,ms_par_lot\n"
        + "\n".join(f"{n},{elapsed:.3f},{images},{ips:.2f},{ms:.2f}" for n, elapsed, images, ips, ms in rows)
        + "\n", encoding="utf-8")
    print(perf.read_text(encoding="utf-8"))
    print(thru.read_text(encoding="utf-8"))
    print("fichiers MediaPipe :", len(files), f"{weight:.2f} MiB")


if __name__ == "__main__":
    main()
