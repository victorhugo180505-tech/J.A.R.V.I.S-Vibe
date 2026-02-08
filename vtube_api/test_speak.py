import pytest


@pytest.mark.vtube
def test_vtube_speak():
    import os

    import pytest

    pytest.importorskip("websocket")
    if os.getenv("ENABLE_VTUBE_TESTS") != "1":
        pytest.skip("ENABLE_VTUBE_TESTS not set")

    from vtube_api.speak import vtube_speak

    vtube_speak("Hola Victor. Si me escuchas, ya quedó el TTS por VTube Studio.")
