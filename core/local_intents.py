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

    if cleaned == "github_write" or ("github" in cleaned and ("issue" in cleaned or "repo" in cleaned)):
        return _build_action("github_write", raw_text)

    if cleaned == "calendar_write" or ("calendario" in cleaned or "evento" in cleaned):
        return _build_action("calendar_write", raw_text)

    return None


def _build_action(action_type: str, raw_text: str) -> ActionRequest:
    action_id = f"intent-{action_type}-{int(time.time() * 1000)}"
    return ActionRequest(
        action_id=action_id,
        type=action_type,
        data={"raw": raw_text} if raw_text else {},
        provider="local",
        requires_confirm=False,
        risk="unknown",
        summary="",
    )
