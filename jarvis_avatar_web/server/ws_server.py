import asyncio, json, threading, traceback, time
import websockets

HOST = "127.0.0.1"
PORT = 8765

clients: set = set()

state = {
    "emotion": "neutral",
    "mouse": {"x": 0.0, "y": 0.0},
    "updated_at": time.time(),
}

def now():
    return time.time()

def dumps(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)

async def safe_send(ws, msg: str) -> bool:
    try:
        await ws.send(msg)
        return True
    except Exception:
        return False

async def broadcast(obj: dict):
    if not clients:
        return
    msg = dumps(obj)
    dead = []
    for ws in list(clients):
        ok = await safe_send(ws, msg)
        if not ok:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)

async def send_full_state(ws):
    payload = {
        "type": "state",
        "emotion": state["emotion"],
        "mouse": state["mouse"],
        "updated_at": state["updated_at"],
    }
    await safe_send(ws, dumps(payload))

def apply_state_update(msg: dict):
    changed = False

    if msg.get("type") == "emotion" and isinstance(msg.get("emotion"), str):
        state["emotion"] = msg["emotion"]
        changed = True

    if msg.get("type") == "mouse":
        x = msg.get("x")
        y = msg.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            x = max(-1.0, min(1.0, float(x)))
            y = max(-1.0, min(1.0, float(y)))
            state["mouse"] = {"x": x, "y": y}
            changed = True

    if changed:
        state["updated_at"] = now()

async def handle_ws(ws):
    clients.add(ws)
    try:
        await send_full_state(ws)

        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            apply_state_update(msg)
            await broadcast(msg)

    except Exception:
        print("🔥 EXCEPCIÓN en handle_ws:")
        traceback.print_exc()
    finally:
        clients.discard(ws)

async def console_loop():
    print(f"WS Hub listo en ws://{HOST}:{PORT}")
    print("Comandos:  s <texto>   |   e <emocion>   | salir")
    print("Extra:     m <x> <y>   (mouse NDC manual -1..1)")

    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, input, "> ")
        line = (line or "").strip()
        if not line:
            continue

        if line.lower() in ("exit", "quit", "salir"):
            break

        if line.startswith("e "):
            emo = line[2:].strip()
            if emo:
                apply_state_update({"type": "emotion", "emotion": emo})
                await broadcast({"type": "emotion", "emotion": emo})
            continue

        if line.startswith("s "):
            text = line[2:].strip()
            if text:
                await broadcast({"type": "say", "emotion": state["emotion"], "text": text})
            continue

        if line.startswith("m "):
            parts = line.split()
            if len(parts) == 3:
                try:
                    x = float(parts[1]); y = float(parts[2])
                    msg = {"type": "mouse", "x": x, "y": y}
                    apply_state_update(msg)
                    await broadcast(msg)
                except ValueError:
                    pass
            continue

        print("Usa: s <texto> | e <emocion> | m <x> <y> | salir")

async def wait_for_stop(stop_event: threading.Event):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, stop_event.wait)

async def serve_ws(stop_event: threading.Event, with_console: bool = True):
    try:
        async with websockets.serve(
            handle_ws,
            HOST,
            PORT,
            max_size=50*1024*1024,# 50MB
            max_queue=32,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
        ):
            if with_console:
                await console_loop()
            else:
                await wait_for_stop(stop_event)
    except Exception:
        print("🔥 EXCEPCIÓN arrancando el servidor:")
        traceback.print_exc()

def start_server_in_thread(with_console: bool = True):
    stop_event = threading.Event()

    def runner():
        asyncio.run(serve_ws(stop_event, with_console=with_console))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return stop_event

if __name__ == "__main__":
    asyncio.run(serve_ws(threading.Event(), with_console=True))
