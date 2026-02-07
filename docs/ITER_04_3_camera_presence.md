# ITER_04.3 Camera presence mapping

## Activar/Desactivar

- Toggle con tecla **C** (console: `[CAM] dynamic ON/OFF`).

## Qué debe verse

- **IDLE**: cámara casi estable + micro breathing (y muy leve).
- **LISTENING**: push-in sutil hacia el avatar + pitch leve.
- **THINKING**: micro-orbit lento (yaw) + pulso de FOV suave.
- **SPEAKING**: casi estable con micro jitter muy leve.

## Checklist visual

- [ ] Transiciones suaves (250–600ms) sin saltos.
- [ ] Clamp de yaw <= 4°, pitch <= 3°.
- [ ] Zoom/push-in <= 8%.
- [ ] FOV delta <= 2°.

## Debug

- Ver logs al cambiar estado: `[CAM] state -> LISTENING`.
