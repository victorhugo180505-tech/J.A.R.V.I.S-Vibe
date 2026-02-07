from __future__ import annotations

import re
from collections import deque
from typing import Callable


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
    session_id: str,
    synthesize_fn: Callable[[str], tuple[str, list]],
    send_fn: Callable[[dict], None],
    subtitle_fn: Callable[[str], None] | None = None,
    session_getter: Callable[[], int],
    session_token: int,
    max_audio_b64: int = 900_000,
    max_chars: int = 450,
    log_fn: Callable[[str], None] | None = None,
) -> int:
    initial_chunks = chunk_text(text, max_chars=max_chars)
    if not initial_chunks:
        return 0

    logger = log_fn or (lambda _: None)
    pending = deque(initial_chunks)
    sent = 0
    total_attempts = 0

    while pending:
        if session_getter() != session_token:
            logger("[TTS] cancelado antes de sintetizar chunk")
            break

        chunk = pending.popleft()
        total_attempts += 1

        audio_b64, visemes = synthesize_fn(chunk)
        audio_len = len(audio_b64 or "")

        if audio_len > max_audio_b64:
            split_result = split_oversize_chunk(chunk)
            logger(
                "[TTS] chunk oversize -> splitting "
                f"chars={len(chunk)} audio_b64_len={audio_len} "
                f"left={len(split_result.left)} right={len(split_result.right)}"
            )
            if split_result.fallback_to_say:
                if subtitle_fn:
                    subtitle_fn(chunk)
                send_fn({
                    "type": "say",
                    "emotion": emotion,
                    "text": chunk,
                })
                sent += 1
                continue
            pending.appendleft(split_result.right)
            pending.appendleft(split_result.left)
            continue

        logger(
            "[TTS] chunk ok "
            f"chars={len(chunk)} audio_b64_len={audio_len} visemes={len(visemes)}"
        )

        if session_getter() != session_token:
            logger("[TTS] cancelado antes de enviar chunk")
            break

        if not audio_b64:
            continue

        if subtitle_fn:
            subtitle_fn(chunk)

        seq = sent + 1
        sent += 1
        is_last = (len(pending) == 0)
        send_fn({
            "type": "tts",
            "emotion": emotion,
            "tts_session_id": session_id,
            "seq": sent,
            "is_last": is_last,
            "subtitle": chunk,
            "audio_b64": audio_b64,
            "visemes": visemes,
        })

        if total_attempts > 1000:
            logger("[TTS] abortando: demasiados splits")
            break

    return sent


class SplitResult:
    def __init__(self, left: str, right: str, fallback_to_say: bool) -> None:
        self.left = left
        self.right = right
        self.fallback_to_say = fallback_to_say


def split_oversize_chunk(text: str, min_chars: int = 30) -> SplitResult:
    cleaned = (text or "").strip()
    if len(cleaned) < min_chars:
        return SplitResult(cleaned, "", True)

    target = int(len(cleaned) * 0.6)
    separators = [",", ";", ":", ".", "?", "!", " "]
    best_idx = -1
    best_dist = len(cleaned)

    for sep in separators:
        for idx in _find_separator_positions(cleaned, sep):
            if idx <= 0 or idx >= len(cleaned) - 1:
                continue
            dist = abs(idx - target)
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        if best_idx != -1:
            break

    if best_idx == -1:
        words = cleaned.split()
        if len(words) < 2:
            return SplitResult(cleaned, "", True)
        mid = len(words) // 2
        left = " ".join(words[:mid]).strip()
        right = " ".join(words[mid:]).strip()
        return SplitResult(left, right, False)

    left = cleaned[:best_idx + 1].strip()
    right = cleaned[best_idx + 1:].strip()
    if not left or not right:
        return SplitResult(cleaned, "", True)
    return SplitResult(left, right, False)


def _find_separator_positions(text: str, sep: str) -> list[int]:
    return [i for i, ch in enumerate(text) if ch == sep]
