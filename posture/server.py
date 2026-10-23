"""Serveur web local : interface de configuration, apercu video et API JSON."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from posture import autostart
from posture.state import state, update_settings, validate

HOST, PORT = "127.0.0.1", 8765  # local uniquement : le flux webcam ne doit jamais sortir de la machine
URL = f"http://{HOST}:{PORT}"
INDEX_FILE = Path(__file__).with_name("index.html")
TEST_ALERT_SECONDS = 6
STREAM_PERIOD = 0.1

_viewers_lock = threading.Lock()


class Server(ThreadingHTTPServer):
    allow_reuse_address = False  # Windows : sinon une 2e instance pourrait ecouter sur le meme port
    daemon_threads = True


def public_settings():
    return {**state.settings, "autostart": autostart.is_enabled()}


def _count_viewer(delta):
    with _viewers_lock:
        state.viewers += delta


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # l'interface interroge l'etat deux fois par seconde : pas de log par requete

    def host_ok(self):
        # Bloque le DNS rebinding : un site externe ne doit pas pouvoir lire la webcam
        port = self.server.server_port
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def send_body(self, body, content_type, code=200):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data, code=200):
        self.send_body(json.dumps(data).encode(), "application/json", code)

    def do_GET(self):
        if not self.host_ok():
            return self.send_error(403)
        if self.path == "/":
            self.send_body(INDEX_FILE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/state":
            self.send_json({"status": state.status, "settings": public_settings()})
        elif self.path == "/video":
            self.stream_video()
        else:
            self.send_error(404)

    def stream_video(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        _count_viewer(+1)
        try:
            while state.running:
                jpeg = state.jpeg
                if jpeg:
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
                time.sleep(STREAM_PERIOD)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # apercu ferme
        finally:
            _count_viewer(-1)

    def do_POST(self):
        # JSON obligatoire : impose un preflight CORS, donc un site externe ne peut pas piloter l'appli
        if not self.host_ok() or self.headers.get("Content-Type") != "application/json":
            return self.send_error(403)
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if not isinstance(data, dict):
                raise ValueError
        except ValueError:
            return self.send_error(400)

        if self.path == "/api/settings":
            try:
                if "autostart" in data:
                    if not isinstance(data["autostart"], bool):
                        raise ValueError("Reglage invalide : autostart")
                    autostart.set_enabled(data.pop("autostart"))
                update_settings(validate(data))
            except ValueError as e:
                return self.send_json({"error": str(e)}, 400)
            self.send_json(public_settings())
        elif self.path == "/api/calibrate":
            state.calib_samples, state.calib_start = [], time.time()
            self.send_json({})
        elif self.path == "/api/test-alert":
            state.test_alert_until = time.time() + TEST_ALERT_SECONDS
            self.send_json({})
        elif self.path == "/api/quit":
            state.running = False
            self.send_json({})
        else:
            self.send_error(404)
