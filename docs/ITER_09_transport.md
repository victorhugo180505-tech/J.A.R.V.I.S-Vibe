# ITER_09 TransportBus (WS first)

## Objetivo

Desacoplar el envío de mensajes del `AvatarWSClient` para que el backend use una
abstracción de transporte sin cambiar los formatos ni puertos actuales.

## Uso

- `WSTransportBus` es la implementación inicial y envía mensajes al WS existente.
- Mantiene los mensajes actuales (`state`, `subtitle`, `emotion`, `confirm`,
  `confirm_result`, `say`, `tts`).

Ejemplo:

```python
bus = WSTransportBus(AvatarWSClient("ws://127.0.0.1:8765"))
bus.send_state({"type": "state", "conversation_state": "IDLE"})
bus.send_subtitle("jarvis", "Hola")
```

## Beneficio

- Permite reemplazar el backend de transporte sin reescribir la lógica de dominio.
