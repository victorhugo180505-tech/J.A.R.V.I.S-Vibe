# ITER_03.5 TTS chunking + cancelación

## Por qué

Azure TTS puede generar `audio_b64` muy grande en respuestas largas y el backend terminaba en fallback.
Ahora se divide el texto en chunks para enviar múltiples `type:"tts"` consecutivos.

## Qué hace

- Divide `speech` por párrafos y oraciones para chunks pequeños.
- Envía varios mensajes `type:"tts"` con el mismo `emotion`.
- Si el usuario hace barge-in (estado pasa a `LISTENING`), se cancelan los chunks restantes.

## Demo (chunking)

1) Arranca el backend:

```bash
python main.py
```

2) Pide una respuesta muy larga.

3) Observa logs tipo:

```
[TTS] chunk 1/5 chars=...
[TTS] chunk 2/5 chars=...
```

4) Escucharás la respuesta completa en varias partes.

## Demo (cancelación)

1) Inicia una respuesta larga.
2) Interrumpe con wake word y otra frase.
3) Los chunks pendientes ya no se envían.
