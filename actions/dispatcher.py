import time

from actions.open_app import open_app
from actions.open_url import open_url
from core.actions_contract import ActionRequest, ActionResult, action_request_from_dict
from core.memory import clear_conversation


_PENDING_ACTION: ActionRequest | None = None


def _is_confirmed(action: ActionRequest) -> bool:
    confirm_value = action.data.get("confirm")
    if confirm_value is None:
        confirm_value = action.data.get("confirmed")
    return bool(confirm_value)


def _emit_confirm(send_fn, action: ActionRequest) -> None:
    if not send_fn:
        return
    send_fn({
        "type": "confirm",
        "action_id": action.action_id,
        "action": {
            "type": action.type,
            "data": action.data,
            "provider": action.provider,
        },
        "requires_confirm": action.requires_confirm,
        "risk": action.risk,
        "summary": action.summary,
    })


def _emit_confirm_result(send_fn, action: ActionRequest, ok: bool) -> None:
    if not send_fn:
        return
    send_fn({
        "type": "confirm_result",
        "action_id": action.action_id,
        "ok": ok,
    })


def _set_post_confirm_state(state) -> None:
    if state is None:
        return
    next_state = "LISTENING" if getattr(state, "mic_enabled", False) else "IDLE"
    state.set_conversation_state(next_state)


def _execute_action(action: ActionRequest) -> ActionResult:
    action_type = action.type
    data = action.data

    if action_type == "none":
        return ActionResult(
            action_id=action.action_id,
            ok=True,
            output="Sin acción.",
            error=None,
            provider=action.provider,
            ts=time.time(),
        )

    if action_type == "open_app":
        app_name = data.get("app_name")
        if not app_name:
            raise ValueError("open_app requiere data.app_name")
        open_app(app_name)
        return ActionResult(
            action_id=action.action_id,
            ok=True,
            output=f"App '{app_name}' abierta.",
            error=None,
            provider=action.provider,
            ts=time.time(),
        )
    if action_type == "open_url":
        url = data.get("url")
        if not url:
            raise ValueError("open_url requiere data.url")
        open_url(url)
        return ActionResult(
            action_id=action.action_id,
            ok=True,
            output=f"URL '{url}' abierta.",
            error=None,
            provider=action.provider,
            ts=time.time(),
        )
    if action_type == "youtube_control":
        from actions.youtube_ext import youtube_control

        output = youtube_control(action.data)
        return ActionResult(
            action_id=action.action_id,
            ok=True,
            output=output,
            error=None,
            provider=action.provider,
            ts=time.time(),
        )
    if action_type == "play_spotify":
        return ActionResult(
            action_id=action.action_id,
            ok=False,
            output=None,
            error="play_spotify no implementado",
            provider=action.provider,
            ts=time.time(),
        )
    if action_type == "reset_memory":
        clear_conversation()
        return ActionResult(
            action_id=action.action_id,
            ok=True,
            output="Memoria reiniciada.",
            error=None,
            provider=action.provider,
            ts=time.time(),
        )
    raise ValueError(f"Acción desconocida: {action_type}")


def confirm_pending_action(*, send_fn=None, state=None) -> ActionResult | None:
    global _PENDING_ACTION
    if _PENDING_ACTION is None:
        return None
    action = _PENDING_ACTION
    _PENDING_ACTION = None
    result = _execute_action(action)
    _emit_confirm_result(send_fn, action, result.ok)
    _set_post_confirm_state(state)
    return result


def cancel_pending_action(*, send_fn=None, state=None) -> ActionResult | None:
    global _PENDING_ACTION
    if _PENDING_ACTION is None:
        return None
    action = _PENDING_ACTION
    _PENDING_ACTION = None
    _emit_confirm_result(send_fn, action, False)
    _set_post_confirm_state(state)
    return ActionResult(
        action_id=action.action_id,
        ok=False,
        output=None,
        error="cancelled",
        provider=action.provider,
        ts=time.time(),
    )


def dispatch_action(action: ActionRequest | dict, *, send_fn=None, state=None) -> ActionResult:
    global _PENDING_ACTION
    if isinstance(action, dict):
        action = action_request_from_dict(action)

    if action.requires_confirm and not _is_confirmed(action):
        _PENDING_ACTION = action
        if state is not None:
            state.set_conversation_state("CONFIRMING")
        _emit_confirm(send_fn, action)
        return ActionResult(
            action_id=action.action_id,
            ok=False,
            output=None,
            error="confirmation_required",
            provider=action.provider,
            ts=time.time(),
        )

    return _execute_action(action)
