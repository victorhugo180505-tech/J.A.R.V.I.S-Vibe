from __future__ import annotations

import time

from core.actions_contract import ActionRequest


def detect_intent(text: str) -> ActionRequest | None:
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return None

    if cleaned in {"borrar memoria", "borra memoria", "delete_memory", "reset_memory"}:
        return _build_action("reset_memory")

    if cleaned in {"screenshare_toggle", "compartir pantalla"}:
        return _build_action("screenshare_toggle")

    if cleaned in {"audio_share_toggle", "compartir audio"}:
        return _build_action("audio_share_toggle")

    return None


def _build_action(action_type: str) -> ActionRequest:
    action_id = f"intent-{action_type}-{int(time.time() * 1000)}"
    return ActionRequest(
        action_id=action_id,
        type=action_type,
        data={},
        provider="local",
        requires_confirm=False,
        risk="unknown",
        summary="",
    )
