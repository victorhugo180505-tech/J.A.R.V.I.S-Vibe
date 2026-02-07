import asyncio
import json
import threading
import time
from queue import Queue, Empty

import websockets

WS_URL = "ws://127.0.0.1:8765"


class AvatarWSClient:
    def __init__(self, url: str = WS_URL, on_message=None):
        self.url = url
        self._q: Queue[dict] = Queue()
        self._thread = None
        self._stop = threading.Event()
        self._on_message = on_message

        self._connected = False
        self._last_err = ""
        self._last_connect_ts = 0.0

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_thread, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def status(self) -> dict:
        return {
            "connected": self._connected,
            "last_error": self._last_err,
            "last_connect_ts": self._last_connect_ts,
            "queue_size": self._q.qsize(),
            "url": self.url,
        }

    # --- API de alto nivel ---
    def set_on_message(self, handler):
        self._on_message = handler

    def send_emotion(self, emotion: str):
        if not emotion:
            return
        self._q.put({"type": "emotion", "emotion": emotion})

    def send_say(self, text: str, emotion: str = "neutral"):
        text = (text or "").strip()
        if not text:
            return
        self._q.put({"type": "say", "emotion": emotion or "neutral", "text": text})

    def send_raw(self, payload: dict):
        if isinstance(payload, dict):
            self._q.put(payload)

    def send_json(self, payload: dict):
        self.send_raw(payload)

    # --- internals ---
    def _run_thread(self):
        asyncio.run(self._main())

    async def _main(self):
        while not self._stop.is_set():
            try:
                async with websockets.connect(
                    self.url,
                    max_size=2**20,
                    ping_interval=15,   # ✅ client keepalive
                    ping_timeout=15,
                    close_timeout=5,
                ) as ws:
                    self._connected = True
                    self._last_err = ""
                    self._last_connect_ts = time.time()

                    # ✅ corre sender y receiver a la vez
                    sender = asyncio.create_task(self._sender_loop(ws))
                    receiver = asyncio.create_task(self._receiver_loop(ws))

                    done, pending = await asyncio.wait(
                        {sender, receiver},
                        return_when=asyncio.FIRST_EXCEPTION
                    )

                    for task in pending:
                        task.cancel()

            except Exception as e:
                self._connected = False
                self._last_err = repr(e)
                await asyncio.sleep(0.6)

    async def _sender_loop(self, ws):
        while not self._stop.is_set():
            try:
                msg = self._q.get_nowait()
            except Empty:
                await asyncio.sleep(0.01)
                continue

            try:
                await ws.send(json.dumps(msg, ensure_ascii=False))
            except Exception as e:
                # re-enqueue para no perderlo
                self._connected = False
                self._last_err = repr(e)
                self._q.put(msg)
                raise

    async def _receiver_loop(self, ws):
        # No usamos mensajes entrantes aquí, pero leer mantiene sano el socket
        try:
            async for raw in ws:
                if self._stop.is_set():
                    break
                if not self._on_message:
                    continue
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                try:
                    self._on_message(msg)
                except Exception:
                    continue
        except Exception as e:
            self._connected = False
            self._last_err = repr(e)
            raise
