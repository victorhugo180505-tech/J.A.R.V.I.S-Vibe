from core.state import JarvisState


def apply_thinking(state: JarvisState) -> None:
    state.set_conversation_state("THINKING")


def apply_speaking(state: JarvisState) -> None:
    state.set_conversation_state("SPEAKING")


def handle_tts_ended(state: JarvisState) -> None:
    next_state = "LISTENING" if state.mic_enabled else "IDLE"
    state.set_conversation_state(next_state)
