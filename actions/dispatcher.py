import time

from actions.open_app import open_app
from actions.open_url import open_url
from core.actions_contract import ActionRequest, ActionResult, action_request_from_dict


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


def dispatch_action(action: ActionRequest | dict, *, send_fn=None, state=None) -> ActionResult:
    if isinstance(action, dict):
        action = action_request_from_dict(action)

    if action.requires_confirm and not _is_confirmed(action):
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
    raise ValueError(f"Acción desconocida: {action_type}")
