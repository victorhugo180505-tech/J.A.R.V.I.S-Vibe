import os
import sys
import time

# Asegurar que la raíz del proyecto está en sys.path
root_dir = os.path.dirname(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.wake_word import WakeWordListener


def on_wake():
    print("🔥 WAKE WORD DETECTED 🔥", flush=True)


def main() -> None:
    listener = WakeWordListener(
        on_detected=on_wake,
        debug=True,         # deja True para ver confidence en consola
        threshold=0.5,
        cooldown_seconds=3.0,
    )
    listener.start()
    print("🎤 Wake word listener activo. Di 'hey jarvis' / 'oye jarvis'.", flush=True)
    print("❌ Ctrl+C para salir.", flush=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⛔ Deteniendo listener...", flush=True)
        listener.stop()


if __name__ == "__main__":
    main()
