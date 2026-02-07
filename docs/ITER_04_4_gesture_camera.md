# ITER_04.4 Gesture + Camera Tuning

## Checklist visual
- **THINKING**: mano derecha a la barbilla (pose sutil, sin romper rig).
- **SPEAKING**: cámara más cerca (push-in 5–10%) y casi sin bob vertical.
- **IDLE/LISTENING**: breathing normal; **THINKING** reducido; **SPEAKING** casi nulo.

## Knobs / parámetros
- **gestureAlpha**: 0→1 en ~0.3s al entrar THINKING, 1→0 en ~0.3s al salir.
- **Pose offsets** (aprox):
  - UpperArm: X -20°, Y +15°, Z +10°
  - LowerArm: X -55°, Y +5°, Z +5°
  - Hand: X -10°, Y +15°, Z -10°
- **Camera SPEAKING**: dist *= 0.93; bob vertical ≈ 0.0002.

## Debug
- **P**: toggle gesture ON/OFF.
- Logs por cambio de estado: `[CAM] state=... gestureAlpha=... dist=... height=...`.
