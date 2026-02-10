from __future__ import annotations

import re
import unicodedata
from typing import Callable


CONFIRM_TOKENS = {"confirmar", "confirm", "si", "sí", "ok", "vale"}
CANCEL_TOKENS = {"cancelar", "cancel", "no", "negativo"}


def normalize_token(text: str) -> str:
    cleaned = (text or "").strip().lower()
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned


def classify_confirm_token(text: str) -> str | None:
    cleaned = normalize_token(text)
    if cleaned in CONFIRM_TOKENS:
        return "confirm"
    if cleaned in CANCEL_TOKENS:
        return "cancel"
    return None


def speak_system_prompt(
    text: str,
    emotion: str = "neutral",
    *,
    set_last_utterance_fn: Callable[[str], None],
    emit_subtitle_fn: Callable[[str, str], None],
    send_emotion_fn: Callable[[str], None],
    send_tts_fn: Callable[[str, str], None],
) -> None:
    cleaned = (text or "").strip()
    if not cleaned:
        return
    set_last_utterance_fn(cleaned)
    emit_subtitle_fn("jarvis", cleaned)
    send_emotion_fn(emotion)
    send_tts_fn(cleaned, emotion)
