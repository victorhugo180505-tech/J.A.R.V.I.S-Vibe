from core.state import JarvisState


def test_ws_state_emitted_on_mic_toggle():
    state = JarvisState()
    sent = []

    def handler(payload: dict):
        sent.append(payload)

    state.set_state_change_handler(handler)

    state.toggle_mic()

    assert sent
    payload = sent[-1]
    assert payload["type"] == "state"
    assert payload["mic_enabled"] is True
    assert payload["conversation_state"] == "LISTENING"


def test_ws_state_emitted_on_conversation_state_change():
    state = JarvisState()
    sent = []

    def handler(payload: dict):
        sent.append(payload)

    state.set_state_change_handler(handler)

    state.set_conversation_state("THINKING")

    assert sent
    payload = sent[-1]
    assert payload["type"] == "state"
    assert payload["conversation_state"] == "THINKING"
    assert payload["mic_enabled"] is False
    assert payload["audio_enabled"] is False
    assert payload["vision_enabled"] is False
    assert payload["wake_active"] is False
