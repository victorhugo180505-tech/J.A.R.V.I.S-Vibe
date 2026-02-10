# ITER_12 OpenClawProvider v1

## Objetivo
Ejecutar integraciones cloud vía OpenClaw con allowlist estricta, confirmación y timeout.

## Variables de entorno
- `OPENCLOW_BASE_URL` (default: `http://127.0.0.1:28789`)
- `OPENCLAW_GATEWAY_TOKEN` (requerido)

## Allowlist
Archivo: `core/action_providers/openclaw_allowlist.json`

Ejemplo:
```json
{
  "allowed_tools": ["calendar_list", "calendar_create", "github_list", "github_create_issue"],
  "tool_aliases": {
    "calendar.list": "calendar_list",
    "calendar.create": "calendar_create",
    "github.list": "github_list",
    "github.create_issue": "github_create_issue"
  }
}
```

## Ejemplos ActionRequest

### github.create_issue (requiere confirm)
```json
{
  "action_id": "action-1",
  "type": "github_write",
  "provider": "openclaw",
  "requires_confirm": true,
  "data": {
    "tool": "github_create_issue",
    "args": {"title": "Bug", "body": "Detalle"},
    "confirmed": true
  }
}
```

### github.list (no requiere confirm)
```json
{
  "action_id": "action-2",
  "type": "github_read",
  "provider": "openclaw",
  "requires_confirm": false,
  "data": {
    "tool": "github_list",
    "args": {}
  }
}
```

## Curl directo a OpenClaw
```bash
curl -s -X POST "$OPENCLOW_BASE_URL/tools/invoke" \\
  -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"tool":"github_list","action":"json","args":{}}'
```

## Seguridad
- Allowlist estricta por herramienta.
- Confirmación obligatoria para create/update/delete (en caller).
- OpenClaw solo por túnel/local (no público).
