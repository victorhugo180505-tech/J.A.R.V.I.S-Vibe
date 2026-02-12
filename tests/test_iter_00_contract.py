import json
from urllib import request, error

import pytest


def _request_json(base_url: str, method: str, path: str, data: dict | None = None):
    url = f"{base_url}{path}"
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
def test_health_ok(control_server_base_url):
    status, payload = _request_json(control_server_base_url, "GET", "/health")
    assert status == 200
    assert payload == {"ok": True}


@pytest.mark.contract
def test_state_keys_present(control_server_base_url):
    status, payload = _request_json(control_server_base_url, "GET", "/state")
    assert status == 200
    for key in (
        "audio_enabled",
        "mic_enabled",
        "vision_enabled",
        "wake_active",
        "conversation_state",
        "last_user_utterance",
        "last_jarvis_utterance",
    ):
        assert key in payload


@pytest.mark.contract
def test_mic_toggle_flips_state(control_server_base_url):
    _, first_toggle = _request_json(control_server_base_url, "POST", "/mic/toggle")
    assert "mic_enabled" in first_toggle

    _, first_state = _request_json(control_server_base_url, "GET", "/state")
    expected_first = "LISTENING" if first_toggle["mic_enabled"] else "IDLE"
    assert first_state["conversation_state"] == expected_first

    _, second_toggle = _request_json(control_server_base_url, "POST", "/mic/toggle")
    assert "mic_enabled" in second_toggle

    _, second_state = _request_json(control_server_base_url, "GET", "/state")
    expected_second = "LISTENING" if second_toggle["mic_enabled"] else "IDLE"
    assert second_state["conversation_state"] == expected_second
