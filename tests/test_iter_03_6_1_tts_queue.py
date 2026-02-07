class DummyPlayer:
    def __init__(self):
        self.queue = []
        self.current_session = None
        self.speaking = False
        self.play_calls = []
        self.subtitle_updates = []

    def stop(self):
        self.speaking = False

    def enqueue(self, msg):
        session = msg.get("tts_session_id")
        if session and session != self.current_session:
            self.current_session = session
            self.queue.clear()
            self.stop()
        self.queue.append(msg)
        self.play_next()

    def play_next(self):
        if self.speaking or not self.queue:
            return
        msg = self.queue.pop(0)
        if msg.get("subtitle"):
            self.subtitle_updates.append(msg["subtitle"])
        self.play_calls.append(msg.get("seq"))
        self.speaking = True

    def on_ended(self):
        self.speaking = False
        self.play_next()


def test_tts_queue_sequential_play():
    player = DummyPlayer()
    msgs = [
        {"tts_session_id": "a", "seq": 1, "subtitle": "uno"},
        {"tts_session_id": "a", "seq": 2, "subtitle": "dos"},
        {"tts_session_id": "a", "seq": 3, "subtitle": "tres"},
    ]
    for msg in msgs:
        player.enqueue(msg)

    assert player.play_calls == [1]
    player.on_ended()
    assert player.play_calls == [1, 2]
    player.on_ended()
    assert player.play_calls == [1, 2, 3]


def test_subtitle_updates_on_play():
    player = DummyPlayer()
    player.enqueue({"tts_session_id": "a", "seq": 1, "subtitle": "hola"})
    assert player.subtitle_updates == ["hola"]
