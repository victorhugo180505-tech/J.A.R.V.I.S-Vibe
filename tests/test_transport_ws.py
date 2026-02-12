from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.transport.ws_bus import WSTransportBus


class FakeAvatarClient:
    def __init__(self):
        self.sent_json = []
        self.sent_emotion = []
        self.sent_say = []
        self.sent_raw = []

    def send_json(self, payload):
        self.sent_json.append(payload)

    def send_emotion(self, emotion):
        self.sent_emotion.append(emotion)

    def send_say(self, text, emotion):
        self.sent_say.append((text, emotion))

    def send_raw(self, payload):
        self.sent_raw.append(payload)

    def status(self):
        return {"ok": True}


def test_ws_bus_send_state():
    client = FakeAvatarClient()
    bus = WSTransportBus(client)
    payload = {"type": "state", "conversation_state": "IDLE"}
    bus.send_state(payload)
    assert client.sent_json == [payload]


def test_ws_bus_send_subtitle():
    client = FakeAvatarClient()
    bus = WSTransportBus(client)
    bus.send_subtitle("user", "hola")
    assert client.sent_json == [{"type": "subtitle", "role": "user", "text": "hola"}]


def test_ws_bus_send_confirm_result():
    client = FakeAvatarClient()
    bus = WSTransportBus(client)
    payload = {"type": "confirm_result", "action_id": "a1", "ok": True}
    bus.send_confirm_result(payload)
    assert client.sent_json == [payload]
