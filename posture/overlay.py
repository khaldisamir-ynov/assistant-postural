"""Signalement a l'ecran, en deux temps :
1. un halo fin qui pulse lentement le long du bord haut (ou bas) de l'ecran ;
2. si la mauvaise posture dure, une pastille « Redressez-vous » avec le motif, dans le coin choisi.
Les fenetres sont traversees par la souris et ne prennent jamais le focus.
"""

import ctypes
import ctypes.wintypes
import math
import time
import tkinter as tk

from posture.state import state

AMBER, CARD, TEXT, MUTED = "#f0a030", "#1f2430", "#ffffff", "#b9c0cc"
KEY = "#010203"  # couleur rendue transparente par Windows
# shortcut: Windows uniquement (styles de fenetre, transparence), ecran principal seulement et zone de travail lue
# au placement ; a revoir pour macOS/Linux, le multi-ecran ou une barre des taches deplacee en cours de route
user32 = ctypes.windll.user32


def work_area():
    """Zone de l'ecran principal hors barre des taches, en pixels."""
    rect = ctypes.wintypes.RECT()
    user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
    return rect.left, rect.top, rect.right, rect.bottom


def floating_window(master=None):
    """Fenetre sans bordure, au premier plan, invisible au depart, traversee par la souris et sans focus."""
    win = tk.Tk() if master is None else tk.Toplevel(master)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.attributes("-alpha", 0.0)
    win.update_idletasks()
    hwnd = user32.GetParent(win.winfo_id())
    style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
    # LAYERED | TRANSPARENT (clics traversants) | TOOLWINDOW (hors Alt+Tab) | NOACTIVATE (jamais le focus)
    user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20 | 0x80 | 0x08000000)
    return win


def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **kw)


class Overlay:
    HALO, PILL_W, PILL_H, MARGIN = 5, 300, 64, 16  # tailles a 100 % d'echelle

    def __init__(self):
        self.root = floating_window()
        self.root.configure(bg=AMBER)  # le halo est la fenetre racine elle-meme
        self.scale = self.root.winfo_fpixels("1i") / 96

        self.pill = floating_window(self.root)
        self.pill.attributes("-transparentcolor", KEY)
        w, h = self.px(self.PILL_W), self.px(self.PILL_H)
        canvas = tk.Canvas(self.pill, width=w, height=h, bg=KEY, highlightthickness=0)
        canvas.pack()
        rounded_rect(canvas, 0, 0, w - 1, h - 1, h // 2, fill=CARD)
        r, cx = self.px(6), self.px(28)
        canvas.create_oval(cx - r, h // 2 - r, cx + r, h // 2 + r, fill=AMBER, outline="")
        x = self.px(46)
        canvas.create_text(x, h // 2 - self.px(10), anchor="w", text="Redressez-vous", fill=TEXT,
                           font=("Segoe UI", 11, "bold"))
        self.detail = canvas.create_text(x, h // 2 + self.px(11), anchor="w", fill=MUTED, font=("Segoe UI", 9))
        self.canvas = canvas

        self.halo_alpha = self.pill_alpha = 0.0
        self.corner = None
        self.tick()

    def px(self, value):
        return round(value * self.scale)

    def place(self, corner):
        if corner == self.corner:
            return
        self.corner = corner
        left, top, right, bottom = work_area()
        halo = self.px(self.HALO)
        self.root.geometry(f"{right - left}x{halo}+{left}+{top if 'top' in corner else bottom - halo}")
        w, h, m = self.px(self.PILL_W), self.px(self.PILL_H), self.px(self.MARGIN)
        x = left + m if "left" in corner else right - w - m
        y = top + halo + m if "top" in corner else bottom - halo - m - h
        self.pill.geometry(f"{w}x{h}+{x}+{y}")

    def tick(self):
        if not state.running:
            return self.root.destroy()
        now = time.time()
        s, st = state.settings, state.status
        test = now < state.test_alert_until
        alert = test or st.get("state") == "alert"
        alert_since = st.get("alert_since") or now
        pill = test or (alert and s["show_pill"] and now - alert_since >= s["escalation_delay"])

        self.place(s["overlay_corner"])
        if pill:
            reasons = [label for label, on in (("Épaules affaissées", st.get("slouch")),
                                               ("Tête en avant", st.get("head"))) if on]
            self.canvas.itemconfig(self.detail, text="Aperçu du rappel" if test else " · ".join(reasons))

        # Pulsation lente du halo : percue en vision peripherique, sans clignoter
        halo_target = 0.55 + 0.3 * math.sin(now * 2) if alert else 0.0
        self.halo_alpha = self.fade(self.root, self.halo_alpha, halo_target)
        self.pill_alpha = self.fade(self.pill, self.pill_alpha, 1.0 if pill else 0.0)
        active = alert or self.halo_alpha or self.pill_alpha
        self.root.after(40 if active else 250, self.tick)

    @staticmethod
    def fade(win, current, target):
        """Rapproche l'opacite de la cible a chaque image : apparitions et disparitions en douceur."""
        value = current + (target - current) * 0.2
        if target == 0 and value < 0.02:
            value = 0.0
        if value != current:
            win.attributes("-alpha", value)
        return value
