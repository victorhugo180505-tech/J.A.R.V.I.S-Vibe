# ITER_01 State Snapshot v1

## Resumen

`GET /state` ahora incluye campos de conversación y últimas frases sin romper los campos existentes.

## Estado (JSON ejemplo)

```json
{
  "audio_enabled": false,
  "mic_enabled": true,
  "vision_enabled": false,
  "wake_active": false,
  "conversation_state": "LISTENING",
  "last_user_utterance": "hola jarvis",
  "last_jarvis_utterance": "Hola, ¿en qué te ayudo?"
}
```

## Reglas mínimas (contract)

- `mic_enabled = true`  -> `conversation_state = "LISTENING"`
- `mic_enabled = false` -> `conversation_state = "IDLE"`

## Campos

- `conversation_state`: `IDLE | LISTENING | THINKING | SPEAKING | CONFIRMING | EXECUTING | DONE`
- `last_user_utterance`: última frase del usuario (string o `null`)
- `last_jarvis_utterance`: última frase de JARVIS (string o `null`)
