# ITER_08 Actions + Policy Gate (claridad y confirmaciones)

## Apps permitidas (open_app)

Valores canónicos de `app_name`:
- `notepad`
- `spotify`

Alias soportados:
- `"bloc de notas"` -> `notepad`
- `"notas"` -> `notepad`
- `"spotify"` -> `spotify`

## Confirmación y cancelación (texto)

Cuando una acción se bloquea por política se emite:

```json
{
  "type": "confirm",
  "action_id": "action-1712345678901",
  "action_type": "reset_memory",
  "summary": "reset_memory (local)",
  "risk": "high"
}
```

Para decidir:
- Escribe **"confirmar"**, **"confirm"**, **"sí"**, **"si"**, **"ok"** o **"vale"** → ejecuta la acción pendiente.
- Escribe **"cancelar"**, **"cancel"**, **"no"** o **"negativo"** → cancela la acción pendiente.

## Intents locales (sin LLM)

Si el texto del usuario coincide con alguno de estos intents, se crea una acción local
para disparar el flujo de confirmación (sin pasar por el LLM):

- "borrar memoria" / "borra memoria" / "delete_memory" / "reset_memory" -> `reset_memory`
- "screenshare_toggle" / "compartir pantalla" -> `screenshare_toggle`
- "audio_share_toggle" / "compartir audio" -> `audio_share_toggle`

## Ejemplo: delete_memory + confirmación verbal

1) Usuario: "delete_memory"
2) Jarvis: "Esta acción es sensible. ¿Confirmas (confirmar/sí) o cancelas (cancelar/no)?"
3) Usuario: "sí"
4) WS:
```json
{"type":"confirm_result","action_id":"action-...","ok":true}
```

Resultado por WS:

```json
{"type":"confirm_result","action_id":"action-1712345678901","ok":true}
```

Si se cancela:

```json
{"type":"confirm_result","action_id":"action-1712345678901","ok":false,"reason":"canceled"}
```

## reset_memory (sensible)

Ejemplo de acción:

```json
{
  "action_id": "action-1712345678901",
  "type": "reset_memory",
  "data": {},
  "provider": "local"
}
```

## delete_memory (alias)

```json
{
  "action_id": "action-1712345678902",
  "type": "delete_memory",
  "data": {},
  "provider": "local"
}
```

## Acciones placeholder (requieren confirmación)

Tipos:
- `calendar_write`
- `github_write`
- `screenshare_toggle`
- `audio_share_toggle`

Ejemplo (github_write):

```json
{
  "action_id": "action-1712345678903",
  "type": "github_write",
  "data": {"intent": "crear issue"},
  "provider": "local"
}
```

Respuesta cuando se confirma:

```json
{
  "action_id": "action-1712345678903",
  "ok": false,
  "error": "not_implemented",
  "output": "Aún no implementado (pendiente OpenClaw/LiveKit)."
}
```
