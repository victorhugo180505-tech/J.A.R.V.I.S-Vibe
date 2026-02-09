import importlib.util
import sys
import time
import types

from actions.dispatcher import confirm_pending_action, dispatch_action
from core.actions_contract import ActionRequest, ActionResult

def _ensure_requests_module() -> None:
    if "requests" in sys.modules:
        return
    if importlib.util.find_spec("requests") is not None:
        return
    fake = types.SimpleNamespace()

    class FakeTimeout(Exception):
        pass

    fake.Timeout = FakeTimeout
    fake.exceptions = types.SimpleNamespace(RequestException=Exception)

    def _post(*_args, **_kwargs):
        raise AssertionError("requests.post should not be called in dispatcher mapping tests")

    fake.post = _post
    sys.modules["requests"] = fake



class DummyState:
    def __init__(self) -> None:
        self.states = []

    def set_conversation_state(self, value: str) -> None:
        self.states.append(value)


def _make_action(action_type: str) -> ActionRequest:
    return ActionRequest(
        action_id=f"action-{action_type}",
        type=action_type,
        data={"intent": "demo"},
        provider="local",
        requires_confirm=True,
        risk="high",
        summary="demo",
    )


def test_calendar_write_confirm_flow_maps_to_openclaw(monkeypatch):
    _ensure_requests_module()
    captured = {}

    def fake_invoke(self, action):
        captured["action"] = action
        return ActionResult(
            action_id=action.action_id,
            ok=True,
            output="ok",
            error=None,
            provider="openclaw",
            ts=time.time(),
        )

    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    monkeypatch.setattr(
        "core.action_providers.openclaw_provider.OpenClawProvider.invoke",
        fake_invoke,
    )

    action = _make_action("calendar_write")
    sends = []
    state = DummyState()

    result = dispatch_action(action, send_fn=sends.append, state=state)
    assert result.error == "confirm_required"

    confirmed = confirm_pending_action(send_fn=sends.append, state=state)
    assert confirmed is not None
    assert captured["action"].data["tool"] == "calendar.create"
    assert captured["action"].data["args"] == {"intent": "demo"}
    assert captured["action"].data["confirmed"] is True


def test_github_write_confirm_flow_maps_to_openclaw(monkeypatch):
    _ensure_requests_module()
    captured = {}

    def fake_invoke(self, action):
        captured["action"] = action
        return ActionResult(
            action_id=action.action_id,
            ok=True,
            output="ok",
            error=None,
            provider="openclaw",
            ts=time.time(),
        )

    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token")
    monkeypatch.setattr(
        "core.action_providers.openclaw_provider.OpenClawProvider.invoke",
        fake_invoke,
    )

    action = _make_action("github_write")
    result = dispatch_action(action, send_fn=None, state=DummyState())
    assert result.error == "confirm_required"

    confirm_pending_action(send_fn=None, state=DummyState())
    assert captured["action"].data["tool"] == "github.create_issue"
    assert captured["action"].data["args"] == {"intent": "demo"}
    assert captured["action"].data["confirmed"] is True
