"""Lancement a l'ouverture de session, sans droits admin : cle Run (Windows) ou LaunchAgent (macOS)."""

import plistlib
import subprocess
import sys
from pathlib import Path

NAME = "AssistantPosture"


def command():
    """Commande de lancement, sans console."""
    if getattr(sys, "frozen", False):  # executable PyInstaller
        return [sys.executable]
    python = Path(sys.executable)
    if sys.platform == "win32":
        python = python.with_name("pythonw.exe")
    # -m posture depuis n'importe ou : necessite le paquet installe (pip install -e .)
    return [str(python), "-m", "posture"]


if sys.platform == "win32":
    import winreg

    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

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
                winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, subprocess.list2cmdline(command()))
            else:
                try:
                    winreg.DeleteValue(key, NAME)
                except FileNotFoundError:
                    pass

else:
    LABEL = "com.assistantposture"
    AGENT = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"

    def is_enabled():
        return AGENT.exists()

    def set_enabled(enabled):
        if enabled:
            AGENT.parent.mkdir(parents=True, exist_ok=True)
            AGENT.write_bytes(plistlib.dumps({"Label": LABEL, "ProgramArguments": command(), "RunAtLoad": True}))
        else:
            AGENT.unlink(missing_ok=True)
