# ITER_03.9 Wakeword barge-in

## Qué hace

- Al detectar "Oye Jarvis" se cancela el TTS actual inmediatamente.
- Se emite `tts_cancel` por WS y el estado pasa a `LISTENING`.
- El avatar limpia la cola y detiene audio al instante.

## Demo reproducible

1) Arranca el backend:

```bash
python main.py
```

2) Pide una respuesta larga.

3) Mientras habla, di: **"Oye Jarvis"**.

4) Debe callarse de inmediato y quedar escuchando.
