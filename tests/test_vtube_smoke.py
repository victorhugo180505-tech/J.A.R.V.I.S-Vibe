import os

import pytest


@pytest.mark.vtube
def test_vtube_smoke():
    pytest.importorskip("websocket")
    if os.getenv("ENABLE_VTUBE_TESTS") != "1":
        pytest.skip("ENABLE_VTUBE_TESTS not set")
