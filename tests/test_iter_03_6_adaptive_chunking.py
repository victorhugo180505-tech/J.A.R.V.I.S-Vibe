from core.tts_chunker import send_tts_chunks


def test_oversize_chunks_are_split_and_sent():
    sent = []
    subtitles = []

    def synthesize_fn(text: str):
        audio_b64 = "a" * (len(text) * 5000)
        return audio_b64, []

    def send_fn(payload: dict):
        sent.append(payload)

    def subtitle_fn(text: str):
        subtitles.append(text)

    session = {"value": 1}

    def get_session():
        return session["value"]

    count = send_tts_chunks(
        "Hola, mundo. " * 20,
        emotion="neutral",
        session_id="session-1",
        synthesize_fn=synthesize_fn,
        send_fn=send_fn,
        subtitle_fn=subtitle_fn,
        session_getter=get_session,
        session_token=1,
        max_audio_b64=900_000,
        max_chars=60,
    )

    assert count == len(sent)
    assert count == len(subtitles)
    assert count > 1
    assert all(payload["type"] in {"tts", "say"} for payload in sent)


def test_subtitle_before_each_chunk():
    sent = []
    subtitles = []

    def synthesize_fn(text: str):
        return "a" * (len(text) * 10), []

    def send_fn(payload: dict):
        sent.append(payload)

    def subtitle_fn(text: str):
        subtitles.append(text)

    session = {"value": 1}

    def get_session():
        return session["value"]

    send_tts_chunks(
        "Hola. " * 10,
        emotion="neutral",
        session_id="session-1",
        synthesize_fn=synthesize_fn,
        send_fn=send_fn,
        subtitle_fn=subtitle_fn,
        session_getter=get_session,
        session_token=1,
        max_audio_b64=900_000,
        max_chars=30,
    )

    assert len(subtitles) == len(sent)
    for subtitle, payload in zip(subtitles, sent):
        if payload["type"] == "tts":
            assert subtitle


def test_cancel_stops_remaining_chunks():
    sent = []
    subtitles = []

    def synthesize_fn(text: str):
        return "a" * (len(text) * 10), []

    session = {"value": 1}

    def get_session():
        return session["value"]

    def subtitle_fn(text: str):
        subtitles.append(text)

    def send_fn(payload: dict):
        sent.append(payload)
        session["value"] = 2

    count = send_tts_chunks(
        "Hola. " * 20,
        emotion="neutral",
        session_id="session-1",
        synthesize_fn=synthesize_fn,
        send_fn=send_fn,
        subtitle_fn=subtitle_fn,
        session_getter=get_session,
        session_token=1,
        max_audio_b64=900_000,
        max_chars=30,
    )

    assert count == 1
    assert len(sent) == 1
    assert len(subtitles) == 1
