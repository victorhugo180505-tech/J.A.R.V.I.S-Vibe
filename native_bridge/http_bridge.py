import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HTTP_HOST = "127.0.0.1"
HTTP_PORT = 8766

TCP_HOST = "127.0.0.1"
TCP_PORT = 8767

_native_conn = None
_lock = threading.Lock()

def tcp_accept_loop():
    """Acepta conexión del native_host (Chrome-launched) por TCP."""
    global _native_conn

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((TCP_HOST, TCP_PORT))
    server.listen(1)

    while True:
        conn, _addr = server.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        with _lock:
            try:
                if _native_conn:
                    _native_conn.close()
            except Exception:
                pass
            _native_conn = conn

class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, obj: dict):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        global _native_conn
        try:
            if self.path != "/command":
                return self._send_json(404, {"ok": False, "error": "Not found"})

            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")

            try:
                payload = json.loads(raw)
            except Exception:
                return self._send_json(400, {"ok": False, "error": "JSON invalido"})

            with _lock:
                conn = _native_conn

            if conn is None:
                return self._send_json(503, {"ok": False, "error": "Chrome/Native host no conectado (abre Chrome con la extension)"})

            try:
                conn.sendall(json.dumps(payload).encode("utf-8"))
            except Exception as e:
                # limpiar conexión muerta
                with _lock:
                    try:
                        if _native_conn:
                            _native_conn.close()
                    except Exception:
                        pass
                    _native_conn = None

                return self._send_json(503, {"ok": False, "error": f"Native host desconectado: {e}"})

            return self._send_json(200, {"ok": True})

        except Exception as e:
            # NUNCA te cierres sin responder
            try:
                return self._send_json(500, {"ok": False, "error": f"Crash http_bridge: {e}"})
            except Exception:
                # si ya no podemos responder, al menos no reventamos el proceso
                return

    def log_message(self, format, *args):
        return

class HttpBridgeServer:
    def __init__(self):
        self._httpd = HTTPServer((HTTP_HOST, HTTP_PORT), Handler)
        self._tcp_thread = threading.Thread(target=tcp_accept_loop, daemon=True)

    def start(self):
        self._tcp_thread.start()
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    def stop(self):
        try:
            self._httpd.shutdown()
        except Exception:
            pass

def main():
    server = HttpBridgeServer()
    server.start()
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        server.stop()

if __name__ == "__main__":
    main()
