from core.tts_chunker import chunk_text, send_tts_chunks


def test_chunker_no_empty_chunks():
    chunks = chunk_text("Hola.\n\n\nAdios!!!")
    assert chunks
    assert all(chunk.strip() for chunk in chunks)


def test_send_tts_chunks_multiple_sends():
    sent = []

    def synthesize_fn(text: str):
        audio_b64 = "a" * (len(text) * 10)
        return audio_b64, [1, 2]

    def send_fn(payload: dict):
        sent.append(payload)

    session = {"value": 1}

    def get_session():
        return session["value"]

    long_text = "Hola. " * 200
    count = send_tts_chunks(
        long_text,
        emotion="neutral",
        synthesize_fn=synthesize_fn,
        send_fn=send_fn,
        session_getter=get_session,
        session_token=1,
        max_audio_b64=900_000,
        max_chars=120,
    )

    assert count > 1
    assert all(item["type"] == "tts" for item in sent)


def test_send_tts_chunks_cancel_midway():
    sent = []

    def synthesize_fn(text: str):
        audio_b64 = "a" * (len(text) * 10)
        return audio_b64, []

    def send_fn(payload: dict):
        sent.append(payload)

    session = {"value": 1}

    def get_session():
        return session["value"]

    def cancel_after_first(payload: dict):
        sent.append(payload)
        session["value"] = 2

    long_text = "Hola. " * 200
    count = send_tts_chunks(
        long_text,
        emotion="neutral",
        synthesize_fn=synthesize_fn,
        send_fn=cancel_after_first,
        session_getter=get_session,
        session_token=1,
        max_audio_b64=900_000,
        max_chars=120,
    )

    assert count == 1
    assert len(sent) == 1
