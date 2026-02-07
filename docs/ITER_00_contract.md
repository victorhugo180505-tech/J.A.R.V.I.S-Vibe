# ITER_00 Contract Tests

## Arrancar backend

Desde la raíz del repo:

```bash
python main.py
```

> Si usas el launcher, también puedes disparar el backend con `tools/wake_jarvis.py`.

## Correr pytest

En otra consola (con el backend arriba):

```bash
pytest -m contract
```

## Curl ejemplos (contract)

```bash
curl -s http://127.0.0.1:8780/health
```

```bash
curl -s http://127.0.0.1:8780/state
```

```bash
curl -s -X POST http://127.0.0.1:8780/mic/toggle
```
