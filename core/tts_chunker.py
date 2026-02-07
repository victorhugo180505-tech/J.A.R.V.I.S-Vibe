from __future__ import annotations

import re
from typing import Callable, Iterable


def _split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in text.split("\n\n")]
    return [p for p in parts if p]


def _split_sentences(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[.!?;:])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _split_words(text: str, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    current = []
    length = 0
    for word in words:
        add_len = len(word) + (1 if current else 0)
        if length + add_len > max_chars and current:
            chunks.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += add_len
    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_text(text: str, max_chars: int = 450) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    for para in _split_paragraphs(cleaned):
        sentences = _split_sentences(para)
        if not sentences:
            continue

        current = ""
        for sentence in sentences:
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(sentence) <= max_chars:
                current = sentence
                continue
            chunks.extend(_split_words(sentence, max_chars))
            current = ""
        if current:
            chunks.append(current)

    return [c for c in chunks if c.strip()]


def send_tts_chunks(
    text: str,
    *,
    emotion: str,
    synthesize_fn: Callable[[str], tuple[str, list]],
    send_fn: Callable[[dict], None],
    session_getter: Callable[[], int],
    session_token: int,
    max_audio_b64: int = 900_000,
    max_chars: int = 450,
    log_fn: Callable[[str], None] | None = None,
) -> int:
    chunks = chunk_text(text, max_chars=max_chars)
    if not chunks:
        return 0

    sent = 0
    total = len(chunks)
    logger = log_fn or (lambda _: None)

    for idx, chunk in enumerate(chunks, start=1):
        if session_getter() != session_token:
            logger("[TTS] cancelado antes de sintetizar chunk")
            break

        audio_b64, visemes = synthesize_fn(chunk)
        audio_len = len(audio_b64 or "")
        logger(f"[TTS] chunk {idx}/{total} chars={len(chunk)} audio_b64_len={audio_len} visemes={len(visemes)}")

        if session_getter() != session_token:
            logger("[TTS] cancelado antes de enviar chunk")
            break

        if not audio_b64:
            continue

        if audio_len > max_audio_b64:
            logger("[TTS] audio demasiado grande para chunk -> omitiendo")
            continue

        send_fn({
            "type": "tts",
            "emotion": emotion,
            "audio_b64": audio_b64,
            "visemes": visemes,
        })
        sent += 1

    return sent
