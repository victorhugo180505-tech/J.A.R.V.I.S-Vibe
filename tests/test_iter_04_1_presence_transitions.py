from core.conversation_flow import apply_speaking, apply_thinking, handle_tts_ended
from core.state import JarvisState


def test_presence_state_transitions_thinking_speaking():
    state = JarvisState()
    state.set_conversation_state("LISTENING")
    apply_thinking(state)
    assert state.conversation_state == "THINKING"
    apply_speaking(state)
    assert state.conversation_state == "SPEAKING"


def test_presence_state_after_tts_ended():
    state = JarvisState()
    state.mic_enabled = True
    state.set_conversation_state("SPEAKING")
    handle_tts_ended(state)
    assert state.conversation_state == "LISTENING"

    state.mic_enabled = False
    state.set_conversation_state("SPEAKING")
    handle_tts_ended(state)
    assert state.conversation_state == "IDLE"
