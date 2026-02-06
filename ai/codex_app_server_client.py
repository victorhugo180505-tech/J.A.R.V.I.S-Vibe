import json, subprocess, threading, queue, itertools, time
from typing import Any, Dict, Optional, List

class CodexAppServer:
    def __init__(self, cmd: List[str]):
        self.cmd = cmd
        self.proc: Optional[subprocess.Popen[str]] = None
        self._rx_thread: Optional[threading.Thread] = None
        self._notifications: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._pending: Dict[int, "queue.Queue[Dict[str, Any]]"] = {}
        self._id = itertools.count(1)
        self._lock = threading.Lock()

    def start(self):
        if self.proc and self.proc.poll() is None:
            return
        self.proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )
        assert self.proc.stdout is not None
        self._rx_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._rx_thread.start()

        # initialize
        rid = self._next_id()
        self._send({"method": "initialize", "id": rid, "params": {"clientInfo": {"name": "jarvis", "version": "0.1.0"}}})
        _ = self._wait(rid, timeout=20)
        self._send({"method": "initialized", "params": {}})

    def stop(self):
        if not self.proc:
            return
        try:
            self.proc.terminate()
        except Exception:
            pass

    def _next_id(self) -> int:
        return next(self._id)

    def _send(self, msg: Dict[str, Any]):
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _reader_loop(self):
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            if "id" in msg:
                with self._lock:
                    q = self._pending.get(msg["id"])
                if q:
                    q.put(msg)
            else:
                self._notifications.put(msg)

    def _wait(self, rid: int, timeout: float = 60) -> Dict[str, Any]:
        q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        with self._lock:
            self._pending[rid] = q
        try:
            return q.get(timeout=timeout)
        finally:
            with self._lock:
                self._pending.pop(rid, None)

    def request(self, method: str, params: Dict[str, Any], timeout: float = 60) -> Any:
        rid = self._next_id()
        self._send({"method": method, "id": rid, "params": params})
        resp = self._wait(rid, timeout=timeout)
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp.get("result")

    def poll(self, timeout: float = 0.2) -> Optional[Dict[str, Any]]:
        try:
            return self._notifications.get(timeout=timeout)
        except queue.Empty:
            return None

    def list_models(self) -> Any:
        return self.request("model/list", {}, timeout=30)

    def start_thread(self, model: str) -> str:
        res = self.request("thread/start", {"model": model}, timeout=30)
        return res["thread"]["id"]

    def run_turn_text(self, thread_id: str, text: str, model: Optional[str] = None) -> str:
        params: Dict[str, Any] = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": text}],
            # IMPORTANTE: evita tool-use peligroso por defecto
            "sandboxPolicy": {"type": "readOnly"},
        }
        if model:
            params["model"] = model

        _ = self.request("turn/start", params, timeout=30)

        chunks: List[str] = []
        final_text: Optional[str] = None
        t0 = time.time()

        while time.time() - t0 < 120:
            ev = self.poll(timeout=0.2)
            if not ev:
                continue
            m = ev.get("method")
            p = ev.get("params", {})

            if m == "item/agentMessage/delta":
                d = p.get("delta", {})
                if isinstance(d, dict) and isinstance(d.get("text"), str):
                    chunks.append(d["text"])

            if m == "item/completed":
                item = p.get("item", {})
                if isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        final_text = item["text"]
                    elif isinstance(item.get("content"), list):
                        texts = []
                        for c in item["content"]:
                            if isinstance(c, dict) and c.get("type") == "text" and isinstance(c.get("text"), str):
                                texts.append(c["text"])
                        if texts:
                            final_text = "\n".join(texts)

            if m == "turn/completed":
                break

        return final_text or "".join(chunks) or ""
