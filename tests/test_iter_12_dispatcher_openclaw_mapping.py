import importlib
import sys
import types

from actions.dispatcher import confirm_pending_action, dispatch_action
from core.actions_contract import ActionRequest


def _install_requests_stub(responses):
    fake = types.SimpleNamespace()

    class FakeTimeout(Exception):
        pass

    fake.Timeout = FakeTimeout
    fake.exceptions = types.SimpleNamespace(RequestException=Exception)
    calls = []

    def _post(url, json, headers, timeout):
        calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if not responses:
            raise AssertionError("Unexpected requests.post call")
        return responses.pop(0)

    fake.post = _post
    sys.modules["requests"] = fake
    return calls


class FakeResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text



class DummyState:
    def __init__(self) -> None:
        self.states = []

    def set_conversation_state(self, value: str) -> None:
        self.states.append(value)


def _make_action(action_type: str, tool: str, *, requires_confirm: bool) -> ActionRequest:
    return ActionRequest(
        action_id=f"action-{action_type}",
        type=action_type,
        data={"tool": tool, "args": {"intent": "demo"}},
        provider="openclaw",
        requires_confirm=requires_confirm,
        risk="high",
        summary="demo",
    )


def test_openclaw_read_alias_invokes_github_tool(monkeypatch):
    calls = _install_requests_stub([FakeResponse(200, "ok")])
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    importlib.reload(importlib.import_module("core.action_providers.openclaw_provider"))

    action = _make_action("github_read", "github.list", requires_confirm=False)
    result = dispatch_action(action, send_fn=None, state=DummyState())

    assert result.ok is True
    assert calls[0]["json"]["tool"] == "github"


def test_openclaw_write_requires_confirm_and_resolves_alias(monkeypatch):
    calls = _install_requests_stub(
        [
            FakeResponse(404, "Tool not available: github_list"),
            FakeResponse(200, "ok"),
        ]
    )
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    importlib.reload(importlib.import_module("core.action_providers.openclaw_provider"))

    action = _make_action("github_write", "github.create_issue", requires_confirm=True)
    result = dispatch_action(action, send_fn=None, state=DummyState())
    assert result.error == "confirm_required"

    confirmed = confirm_pending_action(send_fn=None, state=DummyState())
    assert confirmed is not None
    assert calls[0]["json"]["tool"] == "github"
    assert calls[1]["json"]["tool"] == "github"
