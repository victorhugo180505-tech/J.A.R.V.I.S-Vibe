# ITER_04.2 Presence animations

## Checklist visual

- [ ] **IDLE**: respiración/sway suave.
- [ ] **LISTENING**: lean forward + tilt leve + indicador escucha.
- [ ] **THINKING**: tilt sutil hacia arriba/lado + pulse lento.
- [ ] **SPEAKING**: head bob leve mientras suena audio (lip sync intacto).
- [ ] Transiciones suaves (200–400ms).

## Knobs (valores actuales)

- Idle sway: ~0.003 rad
- Idle breath: ~0.004
- Listening lean: ~0.01–0.03
- Thinking tilt: ~0.08
- Speaking bob: ~0.01

## Cómo validar

1) Arranca backend:

```bash
python main.py
```

2) Observa poses mientras cambian los estados (LISTENING → THINKING → SPEAKING).
