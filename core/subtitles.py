from typing import Callable

from core.state import JarvisState


def emit_subtitle(
    state: JarvisState,
    send_fn: Callable[[dict], None],
    role: str,
    text: str,
) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False

    role_norm = (role or "").strip().lower()
    if role_norm == "user":
        state.set_last_user_utterance(cleaned)
    elif role_norm == "jarvis":
        state.set_last_jarvis_utterance(cleaned)

    payload = {
        "type": "subtitle",
        "role": role_norm or "user",
        "text": cleaned,
    }
    send_fn(payload)
    return True
