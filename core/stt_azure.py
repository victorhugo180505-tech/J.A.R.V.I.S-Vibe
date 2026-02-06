import threading
from typing import Callable, Optional

import azure.cognitiveservices.speech as speechsdk

from core.state import JarvisState


TranscriptCallback = Callable[[str], None]


class AzureSpeechListener:
    def __init__(self, state: JarvisState, key: str, region: str) -> None:
        self.state = state
        self.key = key
        self.region = region
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[TranscriptCallback] = None
        self._recognizer: Optional[speechsdk.SpeechRecognizer] = None

    def start(self, callback: TranscriptCallback) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._callback = callback
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        recognizer = self._recognizer
        if recognizer is not None:
            try:
                recognizer.stop_continuous_recognition()
            except Exception:
                pass

    def _run(self) -> None:
        print("AzureSpeechListener started")
        speech_config = speechsdk.SpeechConfig(subscription=self.key, region=self.region)
        speech_config.speech_recognition_language = "es-MX"
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )
        self._recognizer = recognizer

        def handle_recognized(evt) -> None:
            try:
                if not self.state.mic_enabled:
                    return
                result = evt.result
                text = (result.text or "").strip()
                if not text or not self._callback:
                    return
                print(f"AzureSpeechListener transcript: {text!r}")
                self._callback(text)
            except Exception:
                return

        recognizer.recognized.connect(handle_recognized)

        try:
            recognizer.start_continuous_recognition()
            self._stop.wait()
        finally:
            try:
                recognizer.stop_continuous_recognition()
            except Exception:
                pass
