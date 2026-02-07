# ITER_04.3.1 Camera Fix (LISTENING/THINKING)

## Objetivo
- Corregir la cámara para evitar vista cenital en LISTENING/THINKING.
- Mantener encuadre estable de cara/torso con ancla en cabeza.

## Checklist visual
- **IDLE**: estable, micro breathing apenas perceptible (Y ≤ 0.002).
- **LISTENING**: push-in 3–6%, pitch leve (1–3°), sin elevar en exceso la cámara.
- **THINKING**: micro órbita SOLO yaw (±2–4°), pitch fijo con clamp y sin subida.
- **SPEAKING**: casi estable.

## Validaciones técnicas
- Target anclado a head bone (world position) + pequeño offset vertical.
- Posición de cámara = target + back * dist + up * height (recalculado cada frame).
- Clamps activos: pitch [-15°, +10°], altura ≤ target.y + 0.35, yaw limitado (≤ 4° en THINKING).
- Logs por cambio de estado: `[CAM] state=... pos=(...) target=(...) pitch=... yaw=...`.
