import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from core.state import JarvisState


TranscriptCallback = Callable[[str], None]


@dataclass
class WhisperConfig:
    model_size: str = "base"
    device: str = "cuda"
    compute_type: str = "int8_float16"
    sample_rate: int = 44100
    block_size: int = 4410
    input_device: Optional[int] = 1
    input_channels: int = 2
    speech_threshold: float = 0.012
    min_speech_seconds: float = 0.45
    silence_timeout: float = 0.6
    max_phrase_seconds: float = 6.0
    language: str = "es"


class WhisperListener:
    def __init__(self, state: JarvisState, config: Optional[WhisperConfig] = None) -> None:
        self.state = state
        self.config = config or WhisperConfig()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[TranscriptCallback] = None
        self._model = None
        self._stream = None

    def start(self, callback: TranscriptCallback) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._callback = callback
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _ensure_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            try:
                self._model = WhisperModel(
                    self.config.model_size,
                    device=self.config.device,
                    compute_type=self.config.compute_type,
                )
            except RuntimeError as exc:
                message = str(exc)
                if "cublas" in message.lower() or "cuda" in message.lower():
                    self._model = WhisperModel(
                        self.config.model_size,
                        device="cpu",
                        compute_type="int8",
                    )
                    self.config.device = "cpu"
                    self.config.compute_type = "int8"
                else:
                    raise
        return self._model

    def _run(self) -> None:
        print("WhisperListener._run started")
        try:
            import numpy as np  # type: ignore
            import sounddevice as sd  # type: ignore
        except Exception as exc:
            print(f"WhisperListener._run import error: {exc}")
            return

        cfg = self.config
        self._ensure_model()

        audio_buffer = []
        speech_start: Optional[float] = None
        last_voice = 0.0
        last_rms_log = 0.0

        def reset_buffer():
            nonlocal audio_buffer, speech_start, last_voice
            audio_buffer = []
            speech_start = None
            last_voice = 0.0

        with sd.InputStream(
            samplerate=cfg.sample_rate,
            channels=cfg.input_channels,
            blocksize=cfg.block_size,
            dtype="float32",
            device=cfg.input_device,
        ) as stream:
            self._stream = stream
            print(
                "WhisperListener InputStream opened "
                f"device={cfg.input_device} samplerate={cfg.sample_rate} "
                f"channels={cfg.input_channels}"
            )

            while not self._stop.is_set():
                if not self.state.mic_enabled:
                    reset_buffer()
                    time.sleep(0.1)
                    continue

                data, _ = stream.read(cfg.block_size)
                if cfg.input_channels > 1:
                    mono = data.mean(axis=1)
                else:
                    mono = data[:, 0]
                rms = float(np.sqrt(np.mean(np.square(mono))))
                now = time.time()

                if now - last_rms_log >= 1.0:
                    print(f"WhisperListener RMS={rms:.6f}")
                    last_rms_log = now

                if rms >= cfg.speech_threshold:
                    if speech_start is None:
                        speech_start = now
                    last_voice = now
                    audio_buffer.append(mono.copy())
                else:
                    if audio_buffer:
                        audio_buffer.append(mono.copy())

                if speech_start is None:
                    continue

                speech_duration = now - speech_start
                silence = now - last_voice if last_voice else 0.0

                if speech_duration >= cfg.max_phrase_seconds or silence >= cfg.silence_timeout:
                    if speech_duration >= cfg.min_speech_seconds:
                        samples = np.concatenate(audio_buffer)
                        self._transcribe(samples)
                    reset_buffer()

    def _transcribe(self, audio) -> None:
        print("WhisperListener._transcribe called")
        model = self._ensure_model()
        segments = None
        try:
            segments, _info = model.transcribe(
                audio,
                language=self.config.language,
                beam_size=1,
                vad_filter=False,
            )
            text = self._collect_text(segments)
        except RuntimeError as exc:
            message = str(exc)
            if "cublas" in message.lower() or "cuda" in message.lower():
                self._model = None
                self.config.device = "cpu"
                self.config.compute_type = "int8"
                model = self._ensure_model()
                try:
                    segments, _info = model.transcribe(
                        audio,
                        language=self.config.language,
                        beam_size=1,
                        vad_filter=False,
                    )
                    text = self._collect_text(segments)
                except Exception:
                    return
            else:
                return
        except Exception:
            return

        if text and self._callback:
            print(f"WhisperListener transcript: {text}")
            self._callback(text)

    @staticmethod
    def _collect_text(segments) -> str:
        try:
            return " ".join(seg.text.strip() for seg in segments if seg.text).strip()
        except RuntimeError as exc:
            message = str(exc)
            if "cublas" in message.lower() or "cuda" in message.lower():
                raise
            return ""
