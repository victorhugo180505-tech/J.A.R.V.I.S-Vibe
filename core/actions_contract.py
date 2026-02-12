from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any


@dataclass
class ActionRequest:
    action_id: str
    type: str
    data: dict[str, Any]
    provider: str
    requires_confirm: bool
    risk: str
    summary: str


@dataclass
class ActionResult:
    action_id: str
    ok: bool
    output: str | None
    error: str | None
    provider: str
    ts: float


def action_request_from_dict(payload: dict[str, Any]) -> ActionRequest:
    action_id = str(payload.get("action_id") or f"action-{int(time.time() * 1000)}")
    return ActionRequest(
        action_id=action_id,
        type=str(payload.get("type") or "none"),
        data=payload.get("data") or {},
        provider=str(payload.get("provider") or "local"),
        requires_confirm=bool(payload.get("requires_confirm")),
        risk=str(payload.get("risk") or "unknown"),
        summary=str(payload.get("summary") or ""),
    )
