# ITER_04 Presence mapping (frontend)

## Checklist visual

- [ ] **IDLE**: neutral, sin indicador.
- [ ] **LISTENING**: indicador "Escuchando…" con pulse suave (verde).
- [ ] **THINKING**: indicador "Pensando…" con pulse lento (azul).
- [ ] **SPEAKING**: indicador "Hablando…" (ámbar) + lip sync (ya existe).
- [ ] Transiciones suaves entre estados.

## Cómo validar

1) Arranca backend:

```bash
python main.py
```

2) Observa el indicador en el avatar mientras:
- IDLE: sin indicador.
- Wakeword: cambia a LISTENING.
- Respuesta: SPEAKING.
