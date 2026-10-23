import plistlib
import sys

import pytest

from posture import autostart


def test_command_runs_the_package_without_console():
    cmd = autostart.command()
    assert cmd[-2:] == ["-m", "posture"]
    if sys.platform == "win32":
        assert cmd[0].endswith("pythonw.exe")


@pytest.mark.skipif(sys.platform != "darwin", reason="LaunchAgent : macOS uniquement")
def test_launch_agent_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(autostart, "AGENT", tmp_path / "LaunchAgents" / "agent.plist")
    autostart.set_enabled(True)
    assert autostart.is_enabled()
    agent = plistlib.loads(autostart.AGENT.read_bytes())
    assert agent["RunAtLoad"] and agent["ProgramArguments"] == autostart.command()
    autostart.set_enabled(False)
    assert not autostart.is_enabled()
