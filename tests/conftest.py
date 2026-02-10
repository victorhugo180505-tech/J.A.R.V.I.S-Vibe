import pytest

from core.control_server import ControlServer
from core.state import JarvisState


@pytest.fixture
def control_server_base_url():
    state = JarvisState()
    server = ControlServer(state, host="127.0.0.1", port=0)
    server.start()
    host, port = server.host, server.port
    base_url = f"http://{host}:{port}"
    try:
        yield base_url
    finally:
        server.stop()
