r"""Mesure en usage réel (critères C3 et C5) : l'assistant déjà lancé est observé pendant une durée donnée.

Toutes les secondes : l'état de la détection (/api/state). Toutes les 5 s : le processeur (en % de la machine)
et la mémoire du processus de l'assistant. Aucune image n'est lue ni écrite : seulement des nombres et des états.

Usage : .venv\Scripts\python presentation\mesurer_journee.py 60      (durée en minutes)
Écrit presentation/mesures/journee_<date>.csv, puis affiche le bilan.
"""
import csv
import json
import statistics
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import psutil

URL = "http://127.0.0.1:8765/api/state"
OUT = Path(__file__).resolve().parent / "mesures"
CPU_PERIOD = 5


def assistant():
    """Le processus qui écoute sur le port de l'assistant."""
    for c in psutil.net_connections("tcp"):
        if c.laddr and c.laddr.port == 8765 and c.status == psutil.CONN_LISTEN:
            return psutil.Process(c.pid)
    sys.exit("Assistant introuvable : lancez-le d'abord (python -m posture).")


def main(minutes):
    proc, cores = assistant(), psutil.cpu_count()
    proc.cpu_percent(None)  # amorce : la 1re valeur de psutil vaut toujours 0
    OUT.mkdir(exist_ok=True)
    path = OUT / f"journee_{datetime.now():%Y-%m-%d_%Hh%M}.csv"
    rows, end, tick = [], time.time() + 60 * minutes, 0
    print(f"Mesure de {minutes} min sur le processus {proc.pid} ({cores} coeurs logiques) -> {path.name}", flush=True)
    while time.time() < end:
        t = time.time()
        try:
            status = json.load(urllib.request.urlopen(URL, timeout=2))["status"]
            state = status.get("state", "?")
        except OSError:
            state = "arrete"
        cpu = mem = ""
        if tick % CPU_PERIOD == 0 and tick:
            try:
                cpu = round(proc.cpu_percent(None) / cores, 2)  # % de toute la machine, moyenne sur 5 s
                mem = round(proc.memory_info().rss / 2**20)
            except psutil.Error:
                state = "arrete"
        rows.append({"heure": datetime.now().strftime("%H:%M:%S"), "etat": state, "cpu_machine_pct": cpu, "memoire_mo": mem})
        if state == "arrete":
            break
        tick += 1
        time.sleep(max(0.0, 1 - (time.time() - t)))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    bilan(rows)


def bilan(rows):
    cpu = [r["cpu_machine_pct"] for r in rows if r["cpu_machine_pct"] != ""]
    mem = [r["memoire_mo"] for r in rows if r["memoire_mo"] != ""]
    states = [r["etat"] for r in rows]
    print(f"\nDurée observée : {len(rows)} s")
    if cpu:
        q = statistics.quantiles(cpu, n=20, method="inclusive")
        print(f"Processeur (% de la machine) : moyenne {statistics.mean(cpu):.2f}, p95 {q[-1]:.2f}, max {max(cpu):.2f}  [C3 : <= 5]")
        print(f"Mémoire : médiane {statistics.median(mem)} Mo, max {max(mem)} Mo  [C3 : <= 500]")
    print("Temps par état : " + ", ".join(f"{s} {states.count(s)} s" for s in dict.fromkeys(states)))
    # Episodes : suites consécutives d'un même état, pour relire les essais manuels (C5)
    episodes, start = [], 0
    for i in range(1, len(rows) + 1):
        if i == len(rows) or rows[i]["etat"] != rows[start]["etat"]:
            episodes.append((rows[start]["heure"], rows[start]["etat"], i - start))
            start = i
    print(f"Alertes (passages à l'état alert) : {sum(1 for _, s, _ in episodes if s == 'alert')}")
    print("Changements d'état (heure, état, durée en s) :")
    for h, s, d in episodes:
        print(f"  {h}  {s:13} {d:5d}")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 60)
