from __future__ import annotations

from typing import Protocol


class TransportBus(Protocol):
    def send_state(self, payload: dict) -> None:
        ...

    def send_subtitle(self, role: str, text: str) -> None:
        ...

    def send_emotion(self, emotion: str) -> None:
        ...

    def send_confirm(self, payload: dict) -> None:
        ...

    def send_confirm_result(self, payload: dict) -> None:
        ...

    def send_say(self, text: str, emotion: str) -> None:
        ...

    def send_raw(self, payload: dict) -> None:
        ...

    def status(self) -> dict:
        ...
