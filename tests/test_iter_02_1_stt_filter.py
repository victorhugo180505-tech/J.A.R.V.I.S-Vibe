import json

import azure.cognitiveservices.speech as speechsdk

from core.stt_azure import _should_dispatch_result


class FakeResult:
    def __init__(self, reason, text="", result_json=None):
        self.reason = reason
        self.text = text
        self.json = result_json


def _make_json(confidence):
    return json.dumps({"NBest": [{"Confidence": confidence}]})


def test_no_dispatch_on_empty_text():
    result = FakeResult(speechsdk.ResultReason.RecognizedSpeech, "   ", _make_json(0.9))
    assert _should_dispatch_result(result) is None


def test_no_dispatch_on_symbols_only():
    result = FakeResult(speechsdk.ResultReason.RecognizedSpeech, "!!!", _make_json(0.9))
    assert _should_dispatch_result(result) is None


def test_no_dispatch_on_nomatch():
    result = FakeResult(speechsdk.ResultReason.NoMatch, "hola", _make_json(0.9))
    assert _should_dispatch_result(result) is None


def test_dispatch_on_recognized_with_high_confidence():
    result = FakeResult(speechsdk.ResultReason.RecognizedSpeech, "hola", _make_json(0.9))
    assert _should_dispatch_result(result) == "hola"


def test_no_dispatch_on_low_confidence():
    result = FakeResult(speechsdk.ResultReason.RecognizedSpeech, "hola", _make_json(0.1))
    assert _should_dispatch_result(result) is None
