from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from actions.dispatcher import cancel_pending_action, confirm_pending_action, dispatch_action
from core.actions_contract import ActionRequest
from core.confirm_prompt import classify_confirm_token, speak_system_prompt
from core.local_intents import detect_intent
from core.memory import add_message, clear_conversation, get_conversation
from core.policy_gate import classify_action
from core.state import JarvisState
from core.conversation_flow import handle_tts_ended


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


def test_local_intent_creates_confirm_flow():
    sent = []
    spoken = {"text": None}

    def send_fn(payload):
        sent.append(payload)

    def set_last(text):
        spoken["text"] = text

    def emit_subtitle(role, text):
        spoken["subtitle"] = (role, text)

    def send_emotion(emotion):
        spoken["emotion"] = emotion

    def send_tts(text, emotion):
        spoken["tts"] = (text, emotion)

    intent_action = detect_intent("borrar memoria")
    assert intent_action is not None
    apply_classification(intent_action)

    state = JarvisState()
    blocked = dispatch_action(intent_action, send_fn=send_fn, state=state)
    assert blocked.ok is False
    assert blocked.error == "confirm_required"
    assert sent[-1]["type"] == "confirm"
    assert state.conversation_state == "CONFIRMING"

    speak_system_prompt(
        "Esta acción es sensible. ¿Confirmas (confirmar/sí) o cancelas (cancelar/no)?",
        "neutral",
        set_last_utterance_fn=set_last,
        emit_subtitle_fn=emit_subtitle,
        send_emotion_fn=send_emotion,
        send_tts_fn=send_tts,
    )
    assert spoken["tts"] is not None


def test_local_intent_confirm_executes_reset_memory():
    clear_conversation()
    add_message("user", "hola")
    add_message("assistant", "ok")

    sent = []

    def send_fn(payload):
        sent.append(payload)

    intent_action = detect_intent("reset_memory")
    assert intent_action is not None
    apply_classification(intent_action)
    dispatch_action(intent_action, send_fn=send_fn, state=JarvisState())

    result = confirm_pending_action(send_fn=send_fn, state=JarvisState())
    assert result is not None
    assert result.ok is True
    assert get_conversation() == []


def test_screenshare_placeholder_confirm_not_implemented():
    sent = []

    def send_fn(payload):
        sent.append(payload)

    intent_action = detect_intent("compartir pantalla")
    assert intent_action is not None
    apply_classification(intent_action)
    dispatch_action(intent_action, send_fn=send_fn, state=JarvisState())

    result = confirm_pending_action(send_fn=send_fn, state=JarvisState())
    assert result is not None
    assert result.ok is False
    assert result.error == "not_implemented"


def test_local_intent_github_write_detected():
    action = detect_intent("crear issue en github")
    assert action is not None
    assert action.type == "github_write"
    assert action.data.get("raw")


def test_local_intent_calendar_write_detected():
    action = detect_intent("agrega un evento al calendario")
    assert action is not None
    assert action.type == "calendar_write"
    assert action.data.get("raw")


def test_confirm_cancel_token_variants():
    assert classify_confirm_token("sí") == "confirm"
    assert classify_confirm_token("si") == "confirm"
    assert classify_confirm_token("ok!") == "confirm"
    assert classify_confirm_token("vale") == "confirm"
    assert classify_confirm_token("cancelar...") == "cancel"
    assert classify_confirm_token("no") == "cancel"
    assert classify_confirm_token("negativo") == "cancel"


def test_confirm_cancel_speak_messages():
    calls = {"tts": []}

    def set_last(_text):
        return None

    def emit_subtitle(_role, _text):
        return None

    def send_emotion(_emotion):
        return None

    def send_tts(text, emotion):
        calls["tts"].append((text, emotion))

    speak_system_prompt(
        "Acción confirmada. Listo.",
        "neutral",
        set_last_utterance_fn=set_last,
        emit_subtitle_fn=emit_subtitle,
        send_emotion_fn=send_emotion,
        send_tts_fn=send_tts,
    )
    speak_system_prompt(
        "Acción cancelada.",
        "neutral",
        set_last_utterance_fn=set_last,
        emit_subtitle_fn=emit_subtitle,
        send_emotion_fn=send_emotion,
        send_tts_fn=send_tts,
    )

    assert calls["tts"][0][0].startswith("Acción confirmada")
    assert calls["tts"][1][0] == "Acción cancelada."


def test_speak_system_prompt_calls_tts_and_subtitle():
    calls = {"subtitle": None, "emotion": None, "tts": None, "last": None}

    def set_last(text):
        calls["last"] = text

    def emit_subtitle(role, text):
        calls["subtitle"] = (role, text)

    def send_emotion(emotion):
        calls["emotion"] = emotion

    def send_tts(text, emotion):
        calls["tts"] = (text, emotion)

    speak_system_prompt(
        "Confirma la acción.",
        "neutral",
        set_last_utterance_fn=set_last,
        emit_subtitle_fn=emit_subtitle,
        send_emotion_fn=send_emotion,
        send_tts_fn=send_tts,
    )

    assert calls["last"] == "Confirma la acción."
    assert calls["subtitle"] == ("jarvis", "Confirma la acción.")
    assert calls["emotion"] == "neutral"
    assert calls["tts"] == ("Confirma la acción.", "neutral")


def test_tts_ended_keeps_confirming_when_pending():
    state = JarvisState()
    state.set_conversation_state("SPEAKING")
    handle_tts_ended(state, pending_action=True)
    assert state.conversation_state == "CONFIRMING"
