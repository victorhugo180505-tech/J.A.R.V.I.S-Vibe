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


def _make_action(tool="github_list", confirmed=True):
    return ActionRequest(
        action_id="action-1",
        type="github_read",
        data={"tool": tool, "args": {}, "confirmed": confirmed},
        provider="openclaw",
        requires_confirm=False,
        risk="low",
        summary="",
    )


def test_allowlist_allows(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    monkeypatch.setenv("OPENCLOW_BASE_URL", "http://127.0.0.1:28789")

    called = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        called["url"] = url
        called["headers"] = headers
        called["timeout"] = timeout
        return DummyResponse(200, "ok")

    monkeypatch.setattr("core.action_providers.openclaw_provider.requests.post", fake_post)
    monkeypatch.setattr("core.action_providers.openclaw_provider._load_allowlist", lambda: {
        "allowed_tools": ["github_list"],
        "tool_aliases": {},
    })

    provider = OpenClawProvider()
    result = provider.invoke(_make_action())
    assert result.ok is True
    assert called["timeout"] == 10
    assert called["headers"]["Authorization"].startswith("Bearer ")


def test_allowlist_blocks(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")

    called = {"post": False}

    def fake_post(*_args, **_kwargs):
        called["post"] = True
        return DummyResponse()

    monkeypatch.setattr("core.action_providers.openclaw_provider.requests.post", fake_post)
    monkeypatch.setattr("core.action_providers.openclaw_provider._load_allowlist", lambda: {
        "allowed_tools": ["calendar_list"],
        "tool_aliases": {},
    })

    provider = OpenClawProvider()
    result = provider.invoke(_make_action(tool="github_list"))
    assert result.ok is False
    assert result.error == "not_allowlisted"
    assert called["post"] is False


def test_confirm_gate_enforced(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    monkeypatch.setattr("core.action_providers.openclaw_provider._load_allowlist", lambda: {
        "allowed_tools": ["github_create_issue"],
        "tool_aliases": {},
    })

    provider = OpenClawProvider()
    action = _make_action(tool="github_create_issue", confirmed=False)
    action.requires_confirm = True
    action.data.pop("confirmed", None)
    result = provider.invoke(action)
    assert result.ok is False
    assert result.error == "confirm_required"


def test_timeout_set(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    captured = {}

    def fake_post(*_args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        return DummyResponse(200, "ok")

    monkeypatch.setattr("core.action_providers.openclaw_provider.requests.post", fake_post)
    monkeypatch.setattr("core.action_providers.openclaw_provider._load_allowlist", lambda: {
        "allowed_tools": ["github_list"],
        "tool_aliases": {},
    })

    provider = OpenClawProvider()
    provider.invoke(_make_action())
    assert captured["timeout"] == 10


def test_write_requires_confirm(monkeypatch):
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    monkeypatch.setattr("core.action_providers.openclaw_provider._load_allowlist", lambda: {
        "allowed_tools": ["github_create_issue"],
        "tool_aliases": {},
    })

    provider = OpenClawProvider()
    action = _make_action(tool="github_create_issue", confirmed=False)
    action.requires_confirm = False
    action.data.pop("confirmed", None)
    result = provider.invoke(action)
    assert result.ok is False
    assert result.error == "confirm_required"
