import json
from urllib import request, error

import pytest

BASE_URL = "http://127.0.0.1:8780"


def _request_json(method: str, path: str, data: dict | None = None):
    url = f"{BASE_URL}{path}"
    body = None
    headers = {"Content-Type": "application/json"}

    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = request.Request(url, data=body, method=method, headers=headers)

    try:
        with request.urlopen(req, timeout=2) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, json.loads(payload)
    except error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        raise AssertionError(f"HTTP {exc.code} for {method} {path}: {payload}") from exc
    except Exception as exc:
        raise AssertionError(f"Request failed for {method} {path}: {exc}") from exc


@pytest.mark.contract
def test_health_ok():
    status, payload = _request_json("GET", "/health")
    assert status == 200
    assert payload == {"ok": True}


@pytest.mark.contract
def test_state_keys_present():
    status, payload = _request_json("GET", "/state")
    assert status == 200
    for key in ("audio_enabled", "mic_enabled", "vision_enabled", "wake_active"):
        assert key in payload


@pytest.mark.contract
def test_mic_toggle_flips_state():
    _, first = _request_json("POST", "/mic/toggle")
    assert "mic_enabled" in first

    _, second = _request_json("POST", "/mic/toggle")
    assert "mic_enabled" in second

    assert first["mic_enabled"] != second["mic_enabled"]
