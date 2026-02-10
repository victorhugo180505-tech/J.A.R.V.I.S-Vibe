# ITER_10 NightSession + Consent latch

## Comandos

- `night: <objetivo>`
- `/night <objetivo>`
- `confirmar noche`
- `cancelar noche`

## Flujo

1) Usuario inicia con `night: ...`
2) Jarvis responde con un plan breve y pide confirmación única.
3) `confirmar noche` ejecuta el runner permitido (máximo 60 minutos).
4) Al terminar, se genera un reporte Markdown con checklist y resultados.

## Límites y seguridad

- Tiempo máximo 60 minutos por sesión.
- No se ejecutan comandos arbitrarios.
- Herramientas permitidas: pytest, grep local, listado de archivos y escritura de reporte.

## Reporte

Ruta: `reports/nightly_YYYYMMDD_HHMM_<session_id>.md`

Incluye:
- Objetivo
- Plan con checklist
- Acciones realizadas + timestamps
- Resultado de pytest
- Riesgos/Pendientes
