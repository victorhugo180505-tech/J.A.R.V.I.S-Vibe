from __future__ import annotations


def should_dispatch_action(action_type: str) -> bool:
    return (action_type or "").strip().lower() != "none"
