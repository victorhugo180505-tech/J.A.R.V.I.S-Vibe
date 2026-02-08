from __future__ import annotations

from core.actions_contract import ActionRequest


SENSITIVE_TYPES = {
    "delete_memory",
    "calendar_write",
    "github_write",
    "screenshare_toggle",
    "audio_share_toggle",
}


def classify_action(action: ActionRequest) -> dict[str, str | bool]:
    provider = (action.provider or "local").lower()
    action_type = (action.type or "none").lower()
    requires_confirm = provider == "cloud" or action_type in SENSITIVE_TYPES
    risk = "high" if requires_confirm else "low"
    summary = action.summary or f"{action_type} ({provider})"
    return {
        "requires_confirm": requires_confirm,
        "risk": risk,
        "summary": summary,
    }
