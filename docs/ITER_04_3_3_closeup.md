# ITER_04.3.3 Close-up Base Pose

## Objetivo
- Restaurar el encuadre close-up (cara + poco torso) como base de cámara.
- Usar offsets de presencia muy sutiles sobre esa base.

## Pasos de calibración
1. Arranca el frontend y ajusta el encuadre manualmente (si aplica).
2. Presiona **K** para imprimir en consola:
   - `camera.position`
   - `controls.target` (o `cameraTarget`)
   - `camera.fov`
3. Copia esos valores y reemplaza `BASE_CLOSEUP` en `main.js`.
4. Reinicia y verifica que el encuadre sea close-up sin usar `frameModel()`.

## Recovery
- **F**: ejecuta `frameModel()` solo para recovery (no es el default).

## Presencia (offsets sutiles)
- **LISTENING**: push-in 1–2%, tilt ≤ 1°.
- **THINKING**: micro zoom-out 1–2%, yaw ≤ 2°.
- **SPEAKING**: push-in 2–4%, bobbing casi cero.
