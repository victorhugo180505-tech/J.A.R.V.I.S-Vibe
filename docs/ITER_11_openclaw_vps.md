# ITER_11 OpenClaw en VPS (solo privado)

## Objetivo y threat model
OpenClaw **NO debe ser público**. Solo accesible por túnel (SSH o Tailscale).  
El servicio se ata a `127.0.0.1` para evitar exposición a Internet.

## Requisitos previos
- Docker + Docker Compose
- Acceso SSH a la VPS
- (Opcional) Tailscale en la VPS

## Variables de entorno (sin secretos)
- `OPENCLOW_HOST_PORT` (puerto en localhost de la VPS)
- `OPENCLOW_CONTAINER_PORT` (puerto interno del contenedor)
- `OPENCLOW_IMAGE` (imagen del contenedor)
- `OPENCLOW_BASE_URL` (sugerido para clientes locales)

## Levantar servicio
```bash
cd infra/openclaw
cp .env.example .env
docker compose up -d
docker compose ps
docker compose logs -f openclaw
```

## Acceso por SSH tunnel
```bash
ssh -L <LOCAL_PORT>:127.0.0.1:<OPENCLOW_HOST_PORT> user@vps
```
Luego abre: `http://127.0.0.1:<LOCAL_PORT>/`

## Acceso por Tailscale
El binding es a `127.0.0.1`, por lo que **no** se expone directo en la IP Tailscale.  
Recomendación: usar SSH sobre Tailscale y un túnel local igual que arriba.  
Si decides exponer en `tailscale0`, reconfigura el bind (bajo tu propio riesgo).

## Checklist de seguridad
- [ ] El puerto solo está en `127.0.0.1`
- [ ] No hay puertos abiertos al mundo
- [ ] No se usa `privileged` ni `/var/run/docker.sock`
