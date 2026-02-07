from __future__ import annotations

import re
from typing import Iterable, Optional, Tuple

from core.state import JarvisState


def detect_wake_word(raw_text: str, wake_words: Iterable[str]) -> Tuple[Optional[str], str]:
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return None, ""
    lowered = cleaned.lower()
    for word in wake_words:
        if word in lowered:
            remainder = re.sub(re.escape(word), "", cleaned, flags=re.IGNORECASE).strip(" ,.")
            return word, remainder
    return None, cleaned


def trigger_wake_barge_in(
    state: JarvisState,
    send_fn,
    tts_session: dict,
) -> None:
    tts_session["value"] = int(tts_session.get("value", 0)) + 1
    session_key = tts_session.get("key")
    if session_key:
        send_fn({"type": "tts_cancel", "tts_session_id": session_key})
    state.set_conversation_state("LISTENING")
    state.set_wake_active(True)
