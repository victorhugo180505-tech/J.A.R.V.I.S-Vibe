# ITER_08 Action Providers + Policy Gate

## ActionRequest (entrada)

```json
{
  "action_id": "action-1712345678901",
  "type": "open_app",
  "data": {"app_name": "Spotify"},
  "provider": "local",
  "requires_confirm": false,
  "risk": "low",
  "summary": "open_app (local)"
}
```

## Evento de confirmación (WS)

```json
{
  "type": "confirm",
  "action_id": "action-1712345678901",
  "action": {
    "type": "open_url",
    "data": {"url": "https://example.com"},
    "provider": "cloud"
  },
  "requires_confirm": true,
  "risk": "high",
  "summary": "open_url (cloud)"
}
```

## ActionResult (salida)

```json
{
  "action_id": "action-1712345678901",
  "ok": true,
  "output": "App 'Spotify' abierta.",
  "error": null,
  "provider": "local",
  "ts": 1712345678.901
}
```
