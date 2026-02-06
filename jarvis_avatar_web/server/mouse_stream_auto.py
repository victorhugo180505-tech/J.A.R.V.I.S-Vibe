import asyncio, ctypes, json, threading, time
import websockets
import win32gui
import win32api

WS_URL = "ws://127.0.0.1:8765"
FPS = 60
AVATAR_TITLE_CONTAINS = "JARVIS_AVATAR__5f3c9e"


IDLE_NDC = (0.0, 0.0)

# ---------------- DPI awareness (mejor que shcore) ----------------
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

# -4 = DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)

def set_dpi_awareness():
    try:
        user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

def clamp(v, a, b):
    return a if v < a else b if v > b else v

# ---------------- DWM rect (más estable en Chrome app) ----------------
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]

DWMWA_EXTENDED_FRAME_BOUNDS = 9

def get_window_rect_dwm(hwnd):
    rc = RECT()
    # HRESULT DwmGetWindowAttribute(HWND, DWORD, PVOID, DWORD)
    res = dwmapi.DwmGetWindowAttribute(
        ctypes.c_void_p(hwnd),
        ctypes.c_uint(DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rc),
        ctypes.sizeof(rc)
    )
    if res != 0:
        # fallback
        L, T, R, B = win32gui.GetWindowRect(hwnd)
        return (L, T, R, B)
    return (rc.left, rc.top, rc.right, rc.bottom)

def find_best_window_by_title_contains(substr: str):
    substr = substr.lower()
    best_hwnd = None
    best_area = 0
    best_title = ""

    def enum_cb(hwnd, _):
        nonlocal best_hwnd, best_area, best_title

        if not win32gui.IsWindowVisible(hwnd):
            return

        title = (win32gui.GetWindowText(hwnd) or "").strip()
        if not title:
            return
        if substr not in title.lower():
            return

        L, T, R, B = get_window_rect_dwm(hwnd)
        w = max(0, R - L)
        h = max(0, B - T)
        area = w * h
        if area < 200 * 200:
            return

        if area > best_area:
            best_area = area
            best_hwnd = hwnd
            best_title = title

    win32gui.EnumWindows(enum_cb, None)
    return best_hwnd, best_title

def normalize_mouse_relative_to_window_center(mouse_pt, rc):
    mx, my = mouse_pt
    L, T, R, B = rc
    w = max(1, R - L)
    h = max(1, B - T)

    cx = (L + R) * 0.5
    cy = (T + B) * 0.5

    dx = mx - cx
    dy = my - cy

    # sensibilidad (ajústala si quieres)
    rx = (w * 0.5) * 1.35
    ry = (h * 0.5) * 1.35

    nx = dx / rx
    ny = -dy / ry
    return clamp(nx, -1.0, 1.0), clamp(ny, -1.0, 1.0)

async def send_loop(ws, stop_event: threading.Event, verbose: bool):
    last_hwnd = None
    last_rect = None
    last_dbg = 0.0
    tick = 1.0 / FPS

    while not stop_event.is_set():
        hwnd, title = find_best_window_by_title_contains(AVATAR_TITLE_CONTAINS)
        if hwnd is None:
            await ws.send(json.dumps({"type": "mouse", "x": IDLE_NDC[0], "y": IDLE_NDC[1]}, ensure_ascii=False))
            await asyncio.sleep(0.25)
            continue

        if hwnd != last_hwnd:
            last_hwnd = hwnd
            if verbose:
                print("🎭 Ventana avatar encontrada:", title)

        rc = get_window_rect_dwm(hwnd)
        if rc != last_rect:
            last_rect = rc
            if verbose:
                print("🧩 Rect(DWM) avatar:", rc)

        cx, cy = win32api.GetCursorPos()
        nx, ny = normalize_mouse_relative_to_window_center((cx, cy), rc)

        now = time.time()
        if verbose and now - last_dbg > 3.0:
            print(f"🖱️ cursor=({cx},{cy}) rect={rc} ndc=({nx:.3f},{ny:.3f})")
            last_dbg = now

        await ws.send(json.dumps({"type": "mouse", "x": nx, "y": ny}, ensure_ascii=False))
        await asyncio.sleep(tick)


async def recv_loop(ws, stop_event: threading.Event):
    try:
        async for _ in ws:
            if stop_event.is_set():
                break
    except Exception:
        raise


async def connect_and_stream(stop_event: threading.Event, verbose: bool = True):
    set_dpi_awareness()

    while not stop_event.is_set():
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
                if verbose:
                    print("✅ mouse_stream_auto conectado:", WS_URL)

                sender = asyncio.create_task(send_loop(ws, stop_event, verbose))
                receiver = asyncio.create_task(recv_loop(ws, stop_event))

                done, pending = await asyncio.wait(
                    {sender, receiver},
                    return_when=asyncio.FIRST_EXCEPTION
                )

                for task in pending:
                    task.cancel()

        except Exception as e:
            if verbose:
                print("❌ WS error / desconectado:", repr(e))
                print("🔁 Reintentando en 1s...")
            await asyncio.sleep(1.0)

def start_mouse_stream_in_thread(verbose: bool = True):
    stop_event = threading.Event()

    def runner():
        asyncio.run(connect_and_stream(stop_event, verbose=verbose))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return stop_event

if __name__ == "__main__":
    asyncio.run(connect_and_stream(threading.Event()))
