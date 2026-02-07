# ITER_03.6 Adaptive TTS chunking + subtítulos por chunk

## Por qué

Algunos chunks pueden producir `audio_b64` mayor al límite de WS aunque el texto parezca corto.
Ahora se hace split adaptativo del chunk **hasta que** esté dentro del límite, sin omitir texto.

## Qué hace

- Divide texto por párrafos y oraciones.
- Si un chunk sale oversize, lo divide en 2 sub-chunks buscando un delimitador cercano.
- Antes de cada `type:"tts"` se emite un `type:"subtitle"` con el texto del chunk.
- Si hay barge-in (estado LISTENING), se cancelan los chunks restantes.

## Demo (adaptive chunking)

1) Arranca backend:

```bash
python main.py
```

2) Pide una respuesta larga.

3) Observa logs tipo:

```
[TTS] chunk oversize -> splitting chars=... audio_b64_len=...
[TTS] chunk ok chars=... audio_b64_len=... visemes=...
```

4) Verás subtítulos por chunk mientras habla, y escucharás la respuesta completa.

## Demo (cancelación)

1) Inicia una respuesta larga.
2) Interrumpe con wake word y otra frase.
3) Los chunks pendientes ya no se envían ni se subtitulan.
