import json
import threading
from typing import Callable, Optional

import azure.cognitiveservices.speech as speechsdk

from core.state import JarvisState


TranscriptCallback = Callable[[str], None]
MIN_CONFIDENCE = 0.40


def _extract_confidence(result_json: Optional[str]) -> Optional[float]:
    if not result_json:
        return None
    try:
        payload = json.loads(result_json)
    except json.JSONDecodeError:
        return None
    nbest = payload.get("NBest") or []
    if not nbest:
        return None
    top = nbest[0] or {}
    confidence = top.get("Confidence")
    if confidence is None:
        return None
    try:
        return float(confidence)
    except (TypeError, ValueError):
        return None


def _is_intelligible(text: str, confidence: Optional[float]) -> bool:
    cleaned = (text or "").strip()
    if len(cleaned) < 2:
        return False
    if not any(ch.isalnum() for ch in cleaned):
        return False
    if confidence is not None and confidence < MIN_CONFIDENCE:
        return False
    return True


def _should_dispatch_result(result) -> Optional[str]:
    reason = getattr(result, "reason", None)

    if reason == speechsdk.ResultReason.NoMatch:
        return None

    if reason == speechsdk.ResultReason.Canceled:
        print("[AzureSpeechListener] canceled result recibido")
        return None

    if reason != speechsdk.ResultReason.RecognizedSpeech:
        return None

    text = (getattr(result, "text", "") or "").strip()
    if not text:
        return None

    result_json = getattr(result, "json", None)
    if callable(result_json):
        result_json = result_json()
    confidence = _extract_confidence(result_json)

    if not _is_intelligible(text, confidence):
        return None

    return text


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
        speech_config.output_format = speechsdk.OutputFormat.Detailed
        segmentation_prop = getattr(
            speechsdk.PropertyId,
            "Speech_SegmentationSilenceTimeoutMs",
            None,
        )
        if segmentation_prop is not None:
            speech_config.set_property(segmentation_prop, "3000")
        else:
            speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs,
                "3000",
            )
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
                text = _should_dispatch_result(result)
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
