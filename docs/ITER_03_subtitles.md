# ITER_03 Subtítulos (user/jarvis)

## Qué hace

- Backend emite WS `type:"subtitle"` para usuario y JARVIS.
- Frontend muestra un overlay simple con cola de 2 mensajes y fade-out suave.

## Demo rápida

1) Arranca backend:

```bash
python main.py
```

2) Abre el avatar web/tauri.

3) Di: **“Oye Jarvis”** + una frase.

4) Verás subtítulos de **usuario** (lo que oyó) y luego de **JARVIS** (lo que respondió).

## Payloads

```json
{"type": "subtitle", "role": "user", "text": "hola"}
```

```json
{"type": "subtitle", "role": "jarvis", "text": "Hola, ¿en qué te ayudo?"}
```
