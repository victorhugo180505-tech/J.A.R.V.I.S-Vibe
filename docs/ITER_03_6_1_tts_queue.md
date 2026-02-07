# ITER_03.6.1 TTS queue + subtitle sync

## Problema

Los mensajes `type:"tts"` llegaban en ráfaga y el frontend reiniciaba el audio con cada uno,
interrumpiendo los chunks anteriores.

## Solución

- Se encola cada chunk de audio por `tts_session_id`.
- Solo se reproduce el siguiente chunk cuando termina el anterior.
- El subtítulo se actualiza cuando empieza cada chunk (no al recibirlo).
- Si llega `conversation_state = LISTENING` se limpia la cola y se detiene el audio.

## Demo

1) Arranca el backend:

```bash
python main.py
```

2) Pide una respuesta larga.

3) Escucharás los chunks completos en orden y verás subtítulos por chunk.

4) Interrumpe con wake word/otra frase y la reproducción restante se corta.
