from __future__ import annotations

import time

from core.actions_contract import ActionRequest


def detect_intent(text: str) -> ActionRequest | None:
    raw_text = (text or "").strip()
    cleaned = raw_text.lower()
    if not cleaned:
        return None

    if cleaned in {"borrar memoria", "borra memoria", "delete_memory", "reset_memory"}:
        return _build_action("reset_memory", raw_text)

    if cleaned in {"screenshare_toggle", "compartir pantalla"}:
        return _build_action("screenshare_toggle", raw_text)

    if cleaned in {"audio_share_toggle", "compartir audio"}:
        return _build_action("audio_share_toggle", raw_text)

    if any(token in cleaned for token in (
        "solo privados",
        "privados",
        "cuáles son privados",
        "cuales son privados",
        "dime los privados",
    )) and not any(token in cleaned for token in ("lista", "listar")):
        return _build_action("none", raw_text, data={"kind": "github_cached_visibility", "visibility": "PRIVATE"})

    if any(token in cleaned for token in (
        "solo públicos",
        "solo publicos",
        "públicos",
        "publicos",
        "cuáles son públicos",
        "cuales son publicos",
        "dime los públicos",
        "dime los publicos",
    )) and not any(token in cleaned for token in ("lista", "listar")):
        return _build_action("none", raw_text, data={"kind": "github_cached_visibility", "visibility": "PUBLIC"})

    if any(token in cleaned for token in (
        "dime los nombres de mis repos",
        "nombres de mis repos",
        "cuáles son mis repos",
        "cuales son mis repos",
        "nombres de los repositorios",
    )):
        return _build_action("none", raw_text, data={"kind": "github_cached_names", "visibility": "ALL"})

    if any(token in cleaned for token in ("lista mis repos", "mis repositorios", "mis repos", "listar repos")):
        if "privad" in cleaned:
            cmd = "gh repo list --visibility private --limit 200 --json name,visibility"
        elif "públic" in cleaned or "public" in cleaned:
            cmd = "gh repo list --visibility public --limit 200 --json name,visibility"
        else:
            cmd = "gh repo list --limit 200 --json name,visibility"
        return _build_action("github_write", raw_text, data={"cmd": cmd})

    if cleaned == "github_write" or ("github" in cleaned and ("issue" in cleaned or "repo" in cleaned)):
        return _build_action("github_write", raw_text)

    if cleaned == "calendar_write" or ("calendario" in cleaned or "evento" in cleaned):
        return _build_action("calendar_write", raw_text)

    return None


def _build_action(action_type: str, raw_text: str, data: dict | None = None) -> ActionRequest:
    action_id = f"intent-{action_type}-{int(time.time() * 1000)}"
    return ActionRequest(
        action_id=action_id,
        type=action_type,
        data=data if data is not None else ({"raw": raw_text} if raw_text else {}),
        provider="local",
        requires_confirm=False,
        risk="unknown",
        summary="",
    )
