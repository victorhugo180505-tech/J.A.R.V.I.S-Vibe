# ITER_02.1 Silence segmentation + filtro “no inteligible”

## Qué hace

- Forza salida **FINAL** por silencio (~3s) en Azure STT.
- Ignora resultados no inteligibles (NoMatch, texto vacío, o confidence baja).
- Evita disparar el LLM con basura.

## Cómo probar

1) Arranca el backend:

```bash
python main.py
```

2) Di: **“Oye Jarvis”** o **“Hey Jarvis”** + una frase larga.

3) Pausa **3–4s** para que Azure cierre el enunciado.

4) Debes ver que responde solo después del silencio, sin activar con NoMatch.

## Logs esperados (basado en prints existentes)

- Cuando el listener arranca:
  - `AzureSpeechListener started`
- Cuando hay transcript válido:
  - `AzureSpeechListener transcript: '...'`
