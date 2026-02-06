import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from core.state import JarvisState
from core.vision_capture import VisionCapture


class ControlServer:
    def __init__(self, state: JarvisState, host: str = "127.0.0.1", port: int = 8780) -> None:
        self.state = state
        self.host = host
        self.port = port
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._vision = VisionCapture(state)

    def start(self) -> None:
        if self._httpd:
            return

        server = self

        class Handler(BaseHTTPRequestHandler):
            def _set_cors_headers(self) -> None:
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

            def _send_json(self, code: int, payload: dict) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self) -> None:
                self.send_response(204)
                self._set_cors_headers()
                self.end_headers()

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/health":
                    return self._send_json(200, {"ok": True})
                if parsed.path == "/state":
                    return self._send_json(200, server.state.snapshot())
                if parsed.path == "/vision/snapshot":
                    params = parse_qs(parsed.query or "")
                    monitor = int(params.get("monitor", ["1"])[0])
                    try:
                        data, mime = server._vision.snapshot(monitor)
                    except Exception as exc:
                        return self._send_json(503, {"ok": False, "error": str(exc)})
                    self.send_response(200)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(data)))
                    self._set_cors_headers()
                    self.end_headers()
                    self.wfile.write(data)
                    return
                return self._send_json(404, {"ok": False, "error": "Not found"})

            def do_POST(self) -> None:
                if self.path == "/audio/toggle":
                    value = server.state.toggle_audio()
                    return self._send_json(200, {"audio_enabled": value})
                if self.path == "/mic/toggle":
                    value = server.state.toggle_mic()
                    return self._send_json(200, {"mic_enabled": value})
                if self.path == "/vision/toggle":
                    value = server.state.toggle_vision()
                    return self._send_json(200, {"vision_enabled": value})
                return self._send_json(404, {"ok": False, "error": "Not found"})

            def log_message(self, format: str, *args) -> None:
                return

        self._httpd = HTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._httpd:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        self._httpd = None
