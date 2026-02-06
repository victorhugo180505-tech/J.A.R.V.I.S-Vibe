import time
import subprocess
import sys
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv(str(Path(__file__).resolve().parents[1] / ".env.local"))

# -------------------------------------------------
# PATH FIX (obligatorio para imports)
# -------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import psutil
import requests

from core.wake_word import WakeWordListener

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

MAIN_PY_PATH = REPO_ROOT / "main.py"

TAURI_DEV_CWD = REPO_ROOT / "jarvis_avatar_tauri"
TAURI_DEV_COMMAND = ["npm", "run", "tauri", "dev"]

TAURI_DEV_PROCESS_NAMES = {"node.exe", "npm.exe"}

BACKEND_HEALTH_URL = "http://127.0.0.1:8780/health"
MIC_TOGGLE_URL = "http://127.0.0.1:8780/mic/toggle"

# --- Codex CLI (usado por ai/openai_oauth.py vía `codex exec`)
CODEX_CLI_PWSH = os.getenv("CODEX_CLI_PWSH", r"C:\Users\victo\AppData\Roaming\npm\codex.ps1")


def verify_codex_cli() -> bool:
    """
    Verifica que el wrapper codex.ps1 exista y que responda a --version.
    NO levanta app-server (no hace falta para JARVIS).
    """
    if not os.path.exists(CODEX_CLI_PWSH):
        print(f"[wake_jarvis] ⚠️ CODEX_CLI_PWSH no existe: {CODEX_CLI_PWSH}", flush=True)
        return False

    try:
        # codex.ps1 --version
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", CODEX_CLI_PWSH,
            "--version",
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        ok = (p.returncode == 0)
        if ok:
            ver = (p.stdout or "").strip()
            print(f"[wake_jarvis] 🧠 Codex OK: {ver}", flush=True)
            return True
        else:
            print(f"[wake_jarvis] ⚠️ Codex no respondió bien. rc={p.returncode}", flush=True)
            if p.stderr:
                print(f"[wake_jarvis] stderr: {p.stderr.strip()}", flush=True)
            return False
    except Exception as e:
        print(f"[wake_jarvis] ⚠️ Error verificando Codex: {e}", flush=True)
        return False


# -------------------------------------------------
# (ANTIGUO) CODEX APP SERVER — YA NO SE USA AQUÍ
# -------------------------------------------------
# Nota: `codex app-server` NO es un HTTP server y NO acepta `--port`.
# Si lo corres manualmente, se queda “escuchando” y eso es normal.
#
# CODEX_APP_SERVER_URL = os.getenv("CODEX_APP_SERVER_URL", "http://127.0.0.1:8788")
# CODEX_APP_SERVER_PORT = int(os.getenv("CODEX_APP_SERVER_PORT", "8788"))
#
# def is_codex_running(timeout: float = 0.4) -> bool:
#     try:
#         r = requests.get(CODEX_APP_SERVER_URL.rstrip("/") + "/v1/models", timeout=timeout)
#         return r.status_code == 200
#     except requests.RequestException:
#         return False
#
# def launch_codex_app_server() -> Optional[subprocess.Popen]:
#     # NO USAR: app-server no es HTTP y tu check siempre “fallará”
#     return None


# -------------------------------------------------
# BACKEND
# -------------------------------------------------

def is_backend_running(timeout: float = 0.5) -> bool:
    try:
        r = requests.get(BACKEND_HEALTH_URL, timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def launch_backend() -> Optional[subprocess.Popen]:
    if not MAIN_PY_PATH.exists():
        print("[wake_jarvis] ❌ main.py no encontrado", flush=True)
        return None

    print("[wake_jarvis] 🚀 Lanzando backend en nueva consola...", flush=True)

    return subprocess.Popen(
        [sys.executable, str(MAIN_PY_PATH)],
        cwd=str(REPO_ROOT),
        creationflags=subprocess.CREATE_NEW_CONSOLE,  # 🔥 CLAVE
    )


def wait_for_backend(timeout: float = 15.0) -> bool:
    print("[wake_jarvis] ⏳ Esperando backend (/health)...", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        if is_backend_running():
            print("[wake_jarvis] ✅ Backend activo", flush=True)
            return True
        time.sleep(0.5)
    print("[wake_jarvis] ❌ Backend no respondió a /health", flush=True)
    return False

# -------------------------------------------------
# TAURI (DEV)
# -------------------------------------------------

def is_tauri_running() -> bool:
    for proc in psutil.process_iter(["name"]):
        try:
            name = (proc.info.get("name") or "").lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if name in TAURI_DEV_PROCESS_NAMES:
            return True
    return False


def launch_tauri() -> Optional[subprocess.Popen]:
    if not TAURI_DEV_CWD.exists():
        print("[wake_jarvis] ❌ Carpeta Tauri no encontrada:", TAURI_DEV_CWD, flush=True)
        return None

    print("[wake_jarvis] 🎨 Lanzando Tauri (DEV)...", flush=True)
    return subprocess.Popen(
        TAURI_DEV_COMMAND,
        cwd=str(TAURI_DEV_CWD),
        shell=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

# -------------------------------------------------
# MIC
# -------------------------------------------------

def toggle_mic(timeout: float = 0.5) -> None:
    try:
        print("[wake_jarvis] 🎙️ POST /mic/toggle", flush=True)
        requests.post(MIC_TOGGLE_URL, timeout=timeout)
    except requests.RequestException as e:
        print("[wake_jarvis] ⚠️ Error mic toggle:", e, flush=True)

# -------------------------------------------------
# WAKE WORD CALLBACK
# -------------------------------------------------

def handle_wake_word() -> None:
    print("\n[wake_jarvis] 🔊 Wake word detectada", flush=True)

    # Verifica Codex (para que luego no truene tu openai_oauth.py)
    verify_codex_cli()

    if not is_backend_running():
        launch_backend()
        if not wait_for_backend():
            return

    if not is_tauri_running():
        launch_tauri()
        time.sleep(2.0)

    toggle_mic()

# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main() -> None:
    listener = WakeWordListener(
        on_detected=handle_wake_word,
        wake_word="hey_jarvis_v0.1",
        threshold=0.55,
        cooldown_seconds=3.0,
        debug=False,
    )

    listener.start()
    print("[wake_jarvis] 👂 Escuchando wake word...", flush=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("[wake_jarvis] 🛑 Listener detenido", flush=True)


if __name__ == "__main__":
    main()
