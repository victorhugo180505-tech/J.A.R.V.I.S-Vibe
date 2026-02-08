from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from actions.dispatcher import dispatch_action
from core.actions_contract import ActionRequest
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
    assert result.error == "confirmation_required"
    assert called["open_app"] is False
    assert state.conversation_state == "CONFIRMING"
    assert sent and sent[0]["type"] == "confirm"


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
