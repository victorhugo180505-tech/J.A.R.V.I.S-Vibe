from core.state import JarvisState
from core.wake_bargein import detect_wake_word, trigger_wake_barge_in


def test_detect_wake_word_extracts_remainder():
    matched, remainder = detect_wake_word("Oye Jarvis abre Chrome", ("oye jarvis",))
    assert matched == "oye jarvis"
    assert remainder == "abre Chrome"


def test_trigger_wake_barge_in_sends_cancel_and_listening():
    state = JarvisState()
    sent = []
    tts_session = {"value": 2, "key": "session-2"}

    def send_fn(payload):
        sent.append(payload)

    trigger_wake_barge_in(state, send_fn, tts_session)

    assert state.conversation_state == "LISTENING"
    assert state.wake_active is True
    assert tts_session["value"] == 3
    assert sent == [{"type": "tts_cancel", "tts_session_id": "session-2"}]
