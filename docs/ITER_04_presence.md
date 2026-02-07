# ITER_04 Presence mapping (frontend)

## Checklist visual

- [ ] **IDLE**: neutral, sin indicador.
- [ ] **LISTENING**: indicador "Escuchando…" con pulse suave (verde).
- [ ] **THINKING**: indicador "Pensando…" con pulse lento (azul).
- [ ] **SPEAKING**: indicador "Hablando…" (ámbar) + lip sync (ya existe).
- [ ] Transiciones suaves entre estados.
- [ ] Flujo esperado: LISTENING → THINKING → SPEAKING → (LISTENING/IDLE).

## Cómo validar

1) Arranca backend:

```bash
python main.py
```

2) Observa el indicador en el avatar mientras:
- IDLE: sin indicador.
- Wakeword: cambia a LISTENING.
- Antes del LLM: THINKING.
- TTS activo: SPEAKING.
- Fin de audio: vuelve a LISTENING (si mic on) o IDLE.
