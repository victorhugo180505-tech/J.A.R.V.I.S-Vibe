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
        "action_type": action.type,
        "summary": action.summary,
        "risk": action.risk,
    })


def _emit_confirm_result(send_fn, action: ActionRequest, ok: bool, reason: str | None = None) -> None:
    if not send_fn:
        return
    payload = {
        "type": "confirm_result",
        "action_id": action.action_id,
        "ok": ok,
    }
    if reason:
        payload["reason"] = reason
    send_fn(payload)


def _set_post_confirm_state(state) -> None:
    if state is None:
        return
    state.set_conversation_state("IDLE")


def _execute_action(action: ActionRequest) -> ActionResult:
    action_type = action.type
    data = action.data

    if action.provider == "openclaw":
        from core.action_providers.openclaw_provider import OpenClawProvider

        provider = OpenClawProvider()
        return provider.invoke(action)

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
    if action_type in {"reset_memory", "delete_memory"}:
        clear_conversation()
        return ActionResult(
            action_id=action.action_id,
            ok=True,
            output="Memoria reiniciada.",
            error=None,
            provider=action.provider,
            ts=time.time(),
        )
    if action_type in {"calendar_write", "github_write"}:
        from core.action_providers.openclaw_provider import OpenClawProvider

        tool_name = "calendar.create" if action_type == "calendar_write" else "github.create_issue"
        intent = data.get("intent")
        args = {"intent": intent} if intent else {}
        preserved_flags = {key: data[key] for key in ("confirm", "confirmed") if key in data}
        action.provider = "openclaw"
        action.data = {
            "tool": tool_name,
            "args": args,
            **preserved_flags,
        }
        provider = OpenClawProvider()
        return provider.invoke(action)

    if action_type in {"screenshare_toggle", "audio_share_toggle"}:
        return ActionResult(
            action_id=action.action_id,
            ok=False,
            output="Pendiente integrar LiveKit.",
            error="not_implemented",
            provider=action.provider,
            ts=time.time(),
        )
    return ActionResult(
        action_id=action.action_id,
        ok=False,
        output=None,
        error=f"unknown_action:{action_type}",
        provider=action.provider,
        ts=time.time(),
    )


def confirm_pending_action(*, send_fn=None, state=None) -> ActionResult | None:
    global _PENDING_ACTION
    if _PENDING_ACTION is None:
        return None
    action = _PENDING_ACTION
    _PENDING_ACTION = None
    action.data["confirmed"] = True
    result = _execute_action(action)
    _emit_confirm_result(send_fn, action, result.ok, reason=None if result.ok else result.error)
    _set_post_confirm_state(state)
    return result


def cancel_pending_action(*, send_fn=None, state=None) -> ActionResult | None:
    global _PENDING_ACTION
    if _PENDING_ACTION is None:
        return None
    action = _PENDING_ACTION
    _PENDING_ACTION = None
    _emit_confirm_result(send_fn, action, False, reason="canceled")
    _set_post_confirm_state(state)
    return ActionResult(
        action_id=action.action_id,
        ok=False,
        output=None,
        error="canceled",
        provider=action.provider,
        ts=time.time(),
    )


def has_pending_action() -> bool:
    return _PENDING_ACTION is not None


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
            error="confirm_required",
            provider=action.provider,
            ts=time.time(),
        )

    return _execute_action(action)
