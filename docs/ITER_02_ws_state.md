# ITER_02 WS state

## Payload estable

```json
{
  "type": "state",
  "conversation_state": "LISTENING",
  "mic_enabled": true,
  "audio_enabled": false,
  "vision_enabled": false,
  "wake_active": false
}
```

## Demo (mic toggle)

1) Arranca el backend:

```bash
python main.py
```

2) Haz toggle del mic:

```bash
curl -s -X POST http://127.0.0.1:8780/mic/toggle
```

3) Verifica en el avatar WS que se emitió un mensaje `type:"state"` con el
   `conversation_state` correspondiente.
