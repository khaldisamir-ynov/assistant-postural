"""Signalement a l'ecran, en deux temps :
1. un halo fin qui pulse lentement le long du bord haut (ou bas) de l'ecran ;
2. si la mauvaise posture dure, une pastille « Redressez-vous » avec le motif, dans le coin choisi.
Les fenetres sont traversees par la souris et ne prennent jamais le focus.
"""

import math
import sys
import time
import tkinter as tk

from posture.state import state

AMBER, CARD, TEXT, MUTED = "#f0a030", "#1f2430", "#ffffff", "#b9c0cc"
MAC = sys.platform == "darwin"
# shortcut: ecran principal seulement et zone de travail lue au changement de coin ; a revoir pour le multi-ecran
# ou une barre des taches / un Dock deplace en cours de route

if MAC:
    from AppKit import NSApplication, NSScreen  # PyObjC, deja requis par pystray sous macOS

    TRANSPARENT = "systemTransparent"
    FONT, TITLE_SIZE, DETAIL_SIZE = "Helvetica Neue", 14, 12

    def work_area():
        """Zone de l'ecran principal hors barre des menus et Dock, en points, origine en haut a gauche."""
        screen = NSScreen.mainScreen()
        full, visible = screen.frame(), screen.visibleFrame()
        top = full.size.height - (visible.origin.y + visible.size.height)  # Cocoa compte depuis le bas
        left = visible.origin.x
        return int(left), int(top), int(left + visible.size.width), int(top + visible.size.height)

    def make_passive(win, title):
        """Clics traversants, et presence sur tous les bureaux et par-dessus les apps en plein ecran."""
        win.update_idletasks()
        for ns_window in NSApplication.sharedApplication().windows():
            if ns_window.title() == title:
                ns_window.setIgnoresMouseEvents_(True)
                ns_window.setCollectionBehavior_(1 | 16 | 256)  # CanJoinAllSpaces | Stationary | FullScreenAuxiliary

    def make_transparent(win):
        win.attributes("-transparent", True)
        win.configure(bg=TRANSPARENT)

else:
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32
    TRANSPARENT = "#010203"  # couleur rendue transparente par Windows
    FONT, TITLE_SIZE, DETAIL_SIZE = "Segoe UI", 11, 9

    def work_area():
        """Zone de l'ecran principal hors barre des taches, en pixels."""
        rect = ctypes.wintypes.RECT()
        user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
        return rect.left, rect.top, rect.right, rect.bottom

    def make_passive(win, title):
        """Clics traversants, jamais de focus, absente d'Alt+Tab."""
        win.update_idletasks()
        hwnd = user32.GetParent(win.winfo_id())
        style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
        # LAYERED | TRANSPARENT | TOOLWINDOW | NOACTIVATE
        user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20 | 0x80 | 0x08000000)

    def make_transparent(win):
        win.attributes("-transparentcolor", TRANSPARENT)


def floating_window(title, master=None):
    """Fenetre sans bordure, au premier plan, invisible au depart."""
    win = tk.Tk() if master is None else tk.Toplevel(master)
    win.title(title)  # sert aussi a retrouver la fenetre native sous macOS
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.attributes("-alpha", 0.0)
    make_passive(win, title)
    return win


def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **kw)


class Overlay:
    HALO, PILL_W, PILL_H, MARGIN = 5, 300, 64, 16  # tailles a 100 % d'echelle

    def __init__(self):
        self.root = floating_window("posture-halo")
        self.root.configure(bg=AMBER)  # le halo est la fenetre racine elle-meme
        # Windows compte en pixels physiques (application DPI aware) ; macOS en points, deja mis a l'echelle
        self.scale = 1.0 if MAC else self.root.winfo_fpixels("1i") / 96

        self.pill = floating_window("posture-pill", self.root)
        make_transparent(self.pill)
        w, h = self.px(self.PILL_W), self.px(self.PILL_H)
        canvas = tk.Canvas(self.pill, width=w, height=h, bg=TRANSPARENT, highlightthickness=0)
        canvas.pack()
        rounded_rect(canvas, 0, 0, w - 1, h - 1, h // 2, fill=CARD)
        r, cx = self.px(6), self.px(28)
        canvas.create_oval(cx - r, h // 2 - r, cx + r, h // 2 + r, fill=AMBER, outline="")
        x = self.px(46)
        canvas.create_text(x, h // 2 - self.px(10), anchor="w", text="Redressez-vous", fill=TEXT,
                           font=(FONT, TITLE_SIZE, "bold"))
        self.detail = canvas.create_text(x, h // 2 + self.px(11), anchor="w", fill=MUTED, font=(FONT, DETAIL_SIZE))
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
