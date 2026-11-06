import json
import threading
import urllib.error
import urllib.request

import pytest

from posture import server
from posture.state import state


@pytest.fixture
def base_url():
    httpd = server.Server(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()


def call(url, body=None, headers=None):
    req = urllib.request.Request(url, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def post_json(url, data):
    return call(url, json.dumps(data).encode(), {"Content-Type": "application/json"})


def test_state_and_page(base_url):
    code, body = call(f"{base_url}/api/state")
    assert code == 200 and "status" in json.loads(body)
    assert call(base_url + "/")[0] == 200


def test_foreign_host_is_rejected(base_url):
    assert call(f"{base_url}/api/state", headers={"Host": "evil.example:8765"})[0] == 403


def test_non_json_post_is_rejected(base_url):
    assert call(f"{base_url}/api/settings", b"enabled=false")[0] == 403


def test_settings_are_validated(base_url):
    assert post_json(f"{base_url}/api/settings", {"alert_delay": 999})[0] == 400
    assert post_json(f"{base_url}/api/settings", [1])[0] == 400
    code, body = post_json(f"{base_url}/api/settings", {"alert_delay": 5})
    assert code == 200 and json.loads(body)["alert_delay"] == 5
    assert state.settings["alert_delay"] == 5


def test_second_instance_cannot_bind_same_port(base_url):
    with pytest.raises(OSError):
        server.Server(("127.0.0.1", int(base_url.rsplit(":", 1)[1])), server.Handler)


def test_token_is_validated_and_never_sent_back(base_url):
    assert post_json(f"{base_url}/api/settings", {"coach_token": "pas-un-token"})[0] == 400
    code, body = post_json(f"{base_url}/api/settings", {"coach_token": "hf_" + "a" * 34})
    assert code == 200 and json.loads(body)["coach_token_set"] is True
    assert "hf_" not in call(f"{base_url}/api/state")[1].decode()


def test_coach_needs_token(base_url):
    code, body = post_json(f"{base_url}/api/coach", {})
    assert code == 400 and "token" in json.loads(body)["error"]


def test_places_api(base_url):
    code, body = post_json(f"{base_url}/api/place", {"add": "Café"})
    assert code == 200 and json.loads(body)["place"] == "Café"
    assert post_json(f"{base_url}/api/place", {"select": "Nulle part"})[0] == 400
    assert post_json(f"{base_url}/api/calibrate", {"add": "oui"})[0] == 400
