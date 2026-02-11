from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

pytest.importorskip("requests")

from core.action_providers.openclaw_provider import OpenClawProvider
from core.actions_contract import ActionRequest


class DummyResponse:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


def _make_action(*, action_type="github_write", data=None, confirmed=True, requires_confirm=False):
    payload = {"intent": "crear issue"}
    if data:
        payload.update(data)
    if confirmed:
        payload["confirmed"] = True
    return ActionRequest(
        action_id="action-1",
        type=action_type,
        data=payload,
        provider="openclaw",
        requires_confirm=requires_confirm,
        risk="low",
        summary="",
    )


def test_github_write_requires_confirm_without_http(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    monkeypatch.setattr("core.action_providers.openclaw_provider._load_allowlist", lambda: {
        "allowed_tools": ["sessions_send"],
        "tool_aliases": {},
    })

    called = {"post": False}

    def fake_post(*_args, **_kwargs):
        called["post"] = True
        return DummyResponse(200, "ok")

    monkeypatch.setattr("core.action_providers.openclaw_provider.requests.post", fake_post)

    provider = OpenClawProvider()
    action = _make_action(confirmed=False, requires_confirm=True)
    action.data.pop("confirmed", None)

    result = provider.invoke(action)
    assert result.ok is False
    assert result.error == "confirm_required"
    assert called["post"] is False


def test_github_write_confirmed_calls_sessions_send(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    monkeypatch.setenv("OPENCLOW_BASE_URL", "http://127.0.0.1:28789")
    monkeypatch.setenv("OPENCLOW_SESSION_KEY", "agent:test:session")
    monkeypatch.setenv("OPENCLOW_TIMEOUT_SECONDS", "90")
    monkeypatch.setattr("core.action_providers.openclaw_provider._load_allowlist", lambda: {
        "allowed_tools": ["sessions_send"],
        "tool_aliases": {},
    })

    called = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        called["url"] = url
        called["json"] = json
        called["headers"] = headers
        called["timeout"] = timeout
        return DummyResponse(200, "ok")

    monkeypatch.setattr("core.action_providers.openclaw_provider.requests.post", fake_post)

    provider = OpenClawProvider()
    result = provider.invoke(_make_action(data={"cmd": "gh issue list"}, confirmed=True, requires_confirm=True))

    assert result.ok is True
    assert called["url"].endswith("/tools/invoke")
    assert called["json"]["tool"] == "sessions_send"
    assert called["json"]["args"]["sessionKey"] == "agent:test:session"
    assert "gh issue list" in called["json"]["args"]["message"]
    assert called["timeout"] == 90


def test_allowlist_blocks_sessions_send(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    monkeypatch.setattr("core.action_providers.openclaw_provider._load_allowlist", lambda: {
        "allowed_tools": ["calendar"],
        "tool_aliases": {},
    })

    provider = OpenClawProvider()
    result = provider.invoke(_make_action(confirmed=True))
    assert result.ok is False
    assert result.error == "not_allowlisted"
