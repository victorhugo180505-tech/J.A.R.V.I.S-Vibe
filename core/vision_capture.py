from dataclasses import dataclass
from typing import Optional, Tuple

from core.state import JarvisState


@dataclass
class VisionConfig:
    monitor_index: int = 1


class VisionCapture:
    def __init__(self, state: JarvisState, config: Optional[VisionConfig] = None) -> None:
        self.state = state
        self.config = config or VisionConfig()

    def snapshot(self, monitor_index: Optional[int] = None) -> Tuple[bytes, str]:
        if not self.state.vision_enabled:
            raise RuntimeError("Visión desactivada por el usuario.")

        idx = monitor_index or self.config.monitor_index

        try:
            import mss  # type: ignore
            import mss.tools  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "Falta la dependencia para captura de pantalla. "
                "Instala 'mss' para habilitar visión."
            ) from exc

        with mss.mss() as sct:
            monitors = sct.monitors
            if idx < 1 or idx >= len(monitors):
                raise RuntimeError(f"Monitor inválido: {idx}. Monitores detectados: {len(monitors) - 1}")

            monitor = monitors[idx]
            img = sct.grab(monitor)
            png_bytes = mss.tools.to_png(img.rgb, img.size)
            return png_bytes, "image/png"
