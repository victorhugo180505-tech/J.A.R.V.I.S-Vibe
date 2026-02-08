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
  "action": {
    "type": "reset_memory",
    "data": {},
    "provider": "local"
  },
  "requires_confirm": true,
  "risk": "high",
  "summary": "reset_memory (local)"
}
```

Para decidir:
- Escribe **"confirmar"** o **"confirm"** → ejecuta la acción pendiente.
- Escribe **"cancelar"** o **"cancel"** → cancela la acción pendiente.

Resultado por WS:

```json
{"type":"confirm_result","action_id":"action-1712345678901","ok":true}
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
