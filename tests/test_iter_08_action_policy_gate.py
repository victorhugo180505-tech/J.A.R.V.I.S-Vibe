from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from actions.dispatcher import cancel_pending_action, confirm_pending_action, dispatch_action
from core.actions_contract import ActionRequest
from core.memory import add_message, clear_conversation, get_conversation
from core.policy_gate import classify_action
from core.state import JarvisState


def apply_classification(action: ActionRequest) -> None:
    classification = classify_action(action)
    action.requires_confirm = bool(classification["requires_confirm"])
    action.risk = str(classification["risk"])
    action.summary = str(classification["summary"])


def test_non_sensitive_action_executes():
    action = ActionRequest(
        action_id="action-1",
        type="none",
        data={},
        provider="local",
        requires_confirm=False,
        risk="low",
        summary="",
    )
    apply_classification(action)
    result = dispatch_action(action)
    assert result.ok is True
    assert result.output == "Sin acción."


def test_sensitive_action_without_confirm_blocks(monkeypatch):
    called = {"open_app": False}

    def fake_open_app(_):
        called["open_app"] = True

    monkeypatch.setattr("actions.dispatcher.open_app", fake_open_app)

    state = JarvisState()
    sent = []

    def send_fn(payload):
        sent.append(payload)

    action = ActionRequest(
        action_id="action-2",
        type="open_app",
        data={"app_name": "Notas"},
        provider="cloud",
        requires_confirm=False,
        risk="low",
        summary="",
    )
    apply_classification(action)
    result = dispatch_action(action, send_fn=send_fn, state=state)

    assert result.ok is False
    assert result.error == "confirm_required"
    assert called["open_app"] is False
    assert state.conversation_state == "CONFIRMING"
    assert sent and sent[0]["type"] == "confirm"
    assert sent[0]["action_type"] == "open_app"


def test_sensitive_action_with_confirm_executes(monkeypatch):
    called = {"open_app": False}

    def fake_open_app(_):
        called["open_app"] = True

    monkeypatch.setattr("actions.dispatcher.open_app", fake_open_app)

    action = ActionRequest(
        action_id="action-3",
        type="open_app",
        data={"app_name": "Notas", "confirm": True},
        provider="cloud",
        requires_confirm=False,
        risk="low",
        summary="",
    )
    apply_classification(action)
    result = dispatch_action(action)

    assert result.ok is True
    assert called["open_app"] is True


def test_pending_action_confirm_flow(monkeypatch):
    called = {"open_app": False}

    def fake_open_app(_):
        called["open_app"] = True

    monkeypatch.setattr("actions.dispatcher.open_app", fake_open_app)

    state = JarvisState()
    sent = []

    def send_fn(payload):
        sent.append(payload)

    action = ActionRequest(
        action_id="action-4",
        type="open_app",
        data={"app_name": "Notas"},
        provider="cloud",
        requires_confirm=False,
        risk="low",
        summary="",
    )
    apply_classification(action)
    blocked = dispatch_action(action, send_fn=send_fn, state=state)
    assert blocked.ok is False

    result = confirm_pending_action(send_fn=send_fn, state=state)
    assert result is not None
    assert result.ok is True
    assert called["open_app"] is True
    assert sent[-1]["type"] == "confirm_result"
    assert sent[-1]["ok"] is True


def test_pending_action_cancel_flow(monkeypatch):
    called = {"open_app": False}

    def fake_open_app(_):
        called["open_app"] = True

    monkeypatch.setattr("actions.dispatcher.open_app", fake_open_app)

    state = JarvisState()
    sent = []

    def send_fn(payload):
        sent.append(payload)

    action = ActionRequest(
        action_id="action-5",
        type="open_app",
        data={"app_name": "Notas"},
        provider="cloud",
        requires_confirm=False,
        risk="low",
        summary="",
    )
    apply_classification(action)
    blocked = dispatch_action(action, send_fn=send_fn, state=state)
    assert blocked.ok is False

    result = cancel_pending_action(send_fn=send_fn, state=state)
    assert result is not None
    assert result.ok is False
    assert called["open_app"] is False
    assert sent[-1]["type"] == "confirm_result"
    assert sent[-1]["ok"] is False
    assert sent[-1]["reason"] == "canceled"


def test_reset_memory_confirm_flow():
    clear_conversation()
    add_message("user", "hola")
    add_message("assistant", "ok")
    assert get_conversation()

    sent = []

    def send_fn(payload):
        sent.append(payload)

    action = ActionRequest(
        action_id="action-6",
        type="reset_memory",
        data={},
        provider="local",
        requires_confirm=False,
        risk="low",
        summary="",
    )
    apply_classification(action)
    blocked = dispatch_action(action, send_fn=send_fn, state=JarvisState())
    assert blocked.ok is False
    assert blocked.error == "confirm_required"
    assert sent[-1]["type"] == "confirm"

    result = confirm_pending_action(send_fn=send_fn, state=JarvisState())
    assert result is not None
    assert result.ok is True
    assert get_conversation() == []
    assert sent[-1]["type"] == "confirm_result"
    assert sent[-1]["ok"] is True


def test_placeholder_action_returns_not_implemented():
    sent = []

    def send_fn(payload):
        sent.append(payload)

    action = ActionRequest(
        action_id="action-7",
        type="github_write",
        data={"intent": "crear issue"},
        provider="local",
        requires_confirm=False,
        risk="low",
        summary="",
    )
    apply_classification(action)
    blocked = dispatch_action(action, send_fn=send_fn, state=JarvisState())
    assert blocked.ok is False
    assert blocked.error == "confirm_required"

    result = confirm_pending_action(send_fn=send_fn, state=JarvisState())
    assert result is not None
    assert result.ok is False
    assert result.error == "not_implemented"
