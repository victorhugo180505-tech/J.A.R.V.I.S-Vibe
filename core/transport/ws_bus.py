from __future__ import annotations

from typing import TYPE_CHECKING

from core.transport.base import TransportBus

if TYPE_CHECKING:
    from jarvis_avatar_web.server.avatar_ws_client import AvatarWSClient


class WSTransportBus(TransportBus):
    def __init__(self, client: "AvatarWSClient") -> None:
        self._client = client

    def send_state(self, payload: dict) -> None:
        self._client.send_json(payload)

    def send_subtitle(self, role: str, text: str) -> None:
        self._client.send_json({
            "type": "subtitle",
            "role": (role or "user").strip().lower(),
            "text": (text or "").strip(),
        })

    def send_emotion(self, emotion: str) -> None:
        self._client.send_emotion(emotion)

    def send_confirm(self, payload: dict) -> None:
        self._client.send_json(payload)

    def send_confirm_result(self, payload: dict) -> None:
        self._client.send_json(payload)

    def send_say(self, text: str, emotion: str) -> None:
        self._client.send_say(text, emotion)

    def send_raw(self, payload: dict) -> None:
        self._client.send_raw(payload)

    def status(self) -> dict:
        return self._client.status()
