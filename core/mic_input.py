from dataclasses import dataclass
from typing import Callable, Optional

from core.state import JarvisState


TranscriptCallback = Callable[[str], None]


@dataclass
class MicConfig:
    sample_rate: int = 16000
    channels: int = 1
    block_size: int = 512


class MicInput:
    def __init__(self, state: JarvisState, config: Optional[MicConfig] = None) -> None:
        self.state = state
        self.config = config or MicConfig()
        self._stream = None
        self._callback: Optional[TranscriptCallback] = None

    def start(self, callback: TranscriptCallback) -> None:
        """
        Captura micrófono y llama callback con transcripción.
        Implementación base sin STT: se integra más adelante con VAD + STT local.
        """
        self._callback = callback
        if not self.state.mic_enabled:
            return

        try:
            import sounddevice as sd  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "Falta la dependencia para micrófono. "
                "Instala 'sounddevice' o ajusta el backend."
            ) from exc

        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            blocksize=self.config.block_size,
        )
        self._stream.start()

    def poll(self) -> None:
        if not self._stream or not self._callback:
            return
        if not self.state.mic_enabled:
            return
        data, _ = self._stream.read(self.config.block_size)
        _ = data  # placeholder para integración con VAD + STT

    def stop(self) -> None:
        if self._stream:
            try:
                self._stream.stop()
            finally:
                self._stream = None

    def mute(self) -> None:
        self.state.mic_enabled = False

    def unmute(self) -> None:
        self.state.mic_enabled = True
