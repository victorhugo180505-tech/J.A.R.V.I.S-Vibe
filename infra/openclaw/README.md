# OpenClaw (VPS local-only)

Quickstart:
1) `cp .env.example .env`
2) Edit `OPENCLOW_IMAGE` if needed.
3) `docker compose up -d`
4) `docker compose ps`
5) `docker compose logs -f openclaw`

Notes:
- Service binds to 127.0.0.1 only (use SSH/Tailscale tunnel).
- No public ports are exposed by default.
