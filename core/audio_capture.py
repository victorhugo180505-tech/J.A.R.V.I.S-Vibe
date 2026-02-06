from dataclasses import dataclass
from typing import Callable, Optional

from core.state import JarvisState


AudioFrameCallback = Callable[[bytes, int], None]


@dataclass
class AudioCaptureConfig:
    sample_rate: int = 48000
    channels: int = 2
    block_size: int = 1024


class AudioCapture:
    def __init__(self, state: JarvisState, config: Optional[AudioCaptureConfig] = None) -> None:
        self.state = state
        self.config = config or AudioCaptureConfig()
        self._stream = None
        self._callback: Optional[AudioFrameCallback] = None

    def start(self, callback: AudioFrameCallback) -> None:
        """
        Captura audio del sistema (loopback) y envía frames al callback.
        Requiere una librería local de captura (ej. soundcard).
        """
        self._callback = callback
        if not self.state.audio_enabled:
            return

        try:
            import soundcard as sc  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "Falta la dependencia para loopback de audio. "
                "Instala 'soundcard' o reemplaza por otra librería local."
            ) from exc

        default_speaker = sc.default_speaker()
        if default_speaker is None:
            raise RuntimeError("No se encontró salida de audio para loopback.")

        self._stream = default_speaker.recorder(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            blocksize=self.config.block_size,
        )
        self._stream.__enter__()

    def poll(self) -> None:
        if not self._stream or not self._callback:
            return
        if not self.state.audio_enabled:
            return
        frames = self._stream.record(self.config.block_size)
        self._callback(frames.tobytes(), self.config.sample_rate)

    def stop(self) -> None:
        if self._stream:
            try:
                self._stream.__exit__(None, None, None)
            finally:
                self._stream = None

    def pause(self) -> None:
        self.state.audio_enabled = False

    def resume(self) -> None:
        self.state.audio_enabled = True
