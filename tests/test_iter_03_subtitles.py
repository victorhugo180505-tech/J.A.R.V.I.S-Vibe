from core.state import JarvisState
from core.subtitles import emit_subtitle


def test_emit_subtitle_user_updates_state_and_sends_payload():
    state = JarvisState()
    sent = []

    def sender(payload: dict):
        sent.append(payload)

    assert emit_subtitle(state, sender, "user", "hola") is True

    assert state.last_user_utterance == "hola"
    assert sent
    assert sent[-1] == {"type": "subtitle", "role": "user", "text": "hola"}
