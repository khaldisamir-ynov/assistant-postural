"""Lancement a l'ouverture de session Windows (cle Run de l'utilisateur, sans droits admin)."""

import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
NAME = "AssistantPosture"


def command():
    if getattr(sys, "frozen", False):  # executable PyInstaller
        return f'"{sys.executable}"'
    # pythonw : pas de console. Necessite le paquet installe (pip install -e .) pour -m depuis n'importe ou.
    return f'"{Path(sys.executable).with_name("pythonw.exe")}" -m posture'


def is_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, NAME)
        return True
    except FileNotFoundError:
        return False


def set_enabled(enabled):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, command())
        else:
            try:
                winreg.DeleteValue(key, NAME)
            except FileNotFoundError:
                pass
