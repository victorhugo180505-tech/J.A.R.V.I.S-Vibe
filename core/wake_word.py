import threading
import time
from typing import Callable, Optional

from openwakeword.model import Model

# Nombre del modelo preentrenado de openwakeword
WAKEWORD_KEY = "hey_jarvis_v0.1"


class WakeWordListener:
    """
    Listener de wake word usando openwakeword.

    - Escucha el micrófono en un hilo aparte.
    - Usa el modelo preentrenado 'hey_jarvis_v0.1'.
    - Cuando la confianza supera el umbral y respeta el cooldown,
      llama al callback on_detected().
    """

    def __init__(
        self,
        on_detected: Callable[[], None],
        wake_word: str = WAKEWORD_KEY,
        threshold: float = 0.3,
        cooldown_seconds: float = 3.0,
        sample_rate: int = 16000,
        chunk_size: int = 1280,
        device: Optional[int] = None,
        debug: bool = False,
    ) -> None:
        self._on_detected = on_detected
        self._wake_word = wake_word              # 'hey_jarvis_v0.1'
        self._threshold = threshold              # umbral de activación
        self._cooldown_seconds = cooldown_seconds
        self._sample_rate = sample_rate
        self._chunk_size = chunk_size
        self._device = device
        self._debug = debug

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_trigger = 0.0

    # --------------------------------------------------------------------- #
    # Ciclo de vida del listener
    # --------------------------------------------------------------------- #

    def start(self) -> None:
        """Arranca el hilo que escucha el micrófono."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Detiene el hilo de escucha."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    # --------------------------------------------------------------------- #
    # Hilo interno
    # --------------------------------------------------------------------- #

    def _run(self) -> None:
        try:
            import numpy as np
            import sounddevice as sd
        except Exception as e:
            print("[wakeword] Error importando dependencias:", e, flush=True)
            return

        # Cargar el modelo preentrenado por NOMBRE
        try:
            model = Model(
                wakeword_models=[self._wake_word],  # 'hey_jarvis_v0.1'
            )
        except Exception as e:
            print("[wakeword] Error cargando modelo:", e, flush=True)
            return

        if self._debug:
            print(f"[wakeword] Modelo cargado: {self._wake_word}", flush=True)

        # Abrir stream de audio
        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self._chunk_size,
                device=self._device,
            ) as stream:
                if self._debug:
                    print("[wakeword] Escuchando audio...", flush=True)

                while not self._stop_event.is_set():
                    data, _ = stream.read(self._chunk_size)

                    # data.shape = (frames, 1) -> lo pasamos a vector 1D int16
                    audio = data[:, 0].astype(np.int16)

                    predictions = model.predict(audio)
                    # Sabemos por debug que predictions = {'hey_jarvis_v0.1': float}
                    raw_conf = predictions.get(self._wake_word, 0.0)
                    confidence = float(raw_conf)

                    now = time.time()

                    if self._debug:
                        print(
                            f"[wakeword] confidence={confidence:.6f}",
                            flush=True,
                        )

                    # Checamos umbral + cooldown
                    if (
                        confidence >= self._threshold
                        and (now - self._last_trigger) >= self._cooldown_seconds
                    ):
                        self._last_trigger = now
                        if self._debug:
                            print(
                                "[wakeword] WAKE WORD DETECTED, llamando callback",
                                flush=True,
                            )
                        try:
                            self._on_detected()
                        except Exception as e:
                            print(
                                "[wakeword] Error en callback on_detected:",
                                e,
                                flush=True,
                            )

        except Exception as e:
            print("[wakeword] Error abriendo/leyendo del micrófono:", e, flush=True)
            return
