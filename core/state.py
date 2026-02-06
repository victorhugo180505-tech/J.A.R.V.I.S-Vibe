from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Optional


CONVERSATION_STATES = {
    "IDLE",
    "LISTENING",
    "THINKING",
    "SPEAKING",
    "CONFIRMING",
    "EXECUTING",
    "DONE",
}


@dataclass
class JarvisState:
    audio_enabled: bool = False
    mic_enabled: bool = False
    vision_enabled: bool = False
    wake_active: bool = False
    conversation_state: str = "IDLE"
    last_user_utterance: str | None = None
    last_jarvis_utterance: str | None = None
    lock: Lock = field(default_factory=Lock, repr=False)
    _state_change_handler: Optional[Callable[[dict], None]] = field(default=None, repr=False)

    def toggle_audio(self) -> bool:
        with self.lock:
            self.audio_enabled = not self.audio_enabled
            return self.audio_enabled

    def toggle_mic(self) -> bool:
        with self.lock:
            self.mic_enabled = not self.mic_enabled
            self._set_conversation_state_locked(
                "LISTENING" if self.mic_enabled else "IDLE"
            )
            self._emit_state_locked()
            return self.mic_enabled

    def toggle_vision(self) -> bool:
        with self.lock:
            self.vision_enabled = not self.vision_enabled
            return self.vision_enabled

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "audio_enabled": self.audio_enabled,
                "mic_enabled": self.mic_enabled,
                "vision_enabled": self.vision_enabled,
                "wake_active": self.wake_active,
                "conversation_state": self.conversation_state,
                "last_user_utterance": self.last_user_utterance,
                "last_jarvis_utterance": self.last_jarvis_utterance,
            }

    def set_wake_active(self, active: bool) -> None:
        with self.lock:
            self.wake_active = active

    def set_conversation_state(self, next_state: str) -> None:
        with self.lock:
            self._set_conversation_state_locked(next_state)

    def _set_conversation_state_locked(self, next_state: str) -> None:
        if next_state not in CONVERSATION_STATES:
            raise ValueError(f"Invalid conversation state: {next_state}")
        prev = self.conversation_state
        if prev != next_state:
            print(f"[state] conversation_state {prev} -> {next_state}")
            self.conversation_state = next_state
            self._emit_state_locked()

    def set_last_user_utterance(self, text: str | None) -> None:
        with self.lock:
            self.last_user_utterance = text

    def set_last_jarvis_utterance(self, text: str | None) -> None:
        with self.lock:
            self.last_jarvis_utterance = text

    def set_state_change_handler(self, handler: Optional[Callable[[dict], None]]) -> None:
        with self.lock:
            self._state_change_handler = handler

    def _emit_state_locked(self) -> None:
        if not self._state_change_handler:
            return
        payload = {
            "type": "state",
            "conversation_state": self.conversation_state,
            "mic_enabled": self.mic_enabled,
            "audio_enabled": self.audio_enabled,
            "vision_enabled": self.vision_enabled,
            "wake_active": self.wake_active,
        }
        try:
            self._state_change_handler(payload)
        except Exception as exc:
            print(f"[state] ⚠️ Error enviando state WS: {exc}")


state = JarvisState()
