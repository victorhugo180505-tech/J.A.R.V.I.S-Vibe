from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

from core.actions_contract import ActionRequest, ActionResult


ALLOWLIST_PATH = Path(__file__).with_name("openclaw_allowlist.json")
DEFAULT_BASE_URL = "http://127.0.0.1:28789"
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_SESSION_KEY = "agent:main:main"


class OpenClawProvider:
    def __init__(self) -> None:
        self.base_url = os.getenv("OPENCLOW_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.token = os.getenv("OPENCLAW_GATEWAY_TOKEN")
        if not self.token:
            raise ValueError("OPENCLAW_GATEWAY_TOKEN is required")
        self.session_key = os.getenv("OPENCLOW_SESSION_KEY", DEFAULT_SESSION_KEY)
        self.timeout_seconds = int(os.getenv("OPENCLOW_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
        self.allowlist = _load_allowlist()

    def invoke(self, action_request: ActionRequest) -> ActionResult:
        if action_request.type == "github_write":
            return self._invoke_github_write(action_request)

        raw_tool = _raw_tool_name(action_request)
        tool_name = _resolve_tool_name(action_request, self.allowlist)
        if not tool_name:
            return _result(action_request, ok=False, error="missing_tool")

        if not _is_allowlisted(tool_name, self.allowlist):
            return _result(action_request, ok=False, error="not_allowlisted")

        if _is_write_action(raw_tool) and not _is_confirmed(action_request):
            return _result(action_request, ok=False, error="confirm_required")

        headers = {"Authorization": f"Bearer {self.token}"}
        args = action_request.data.get("args", {})
        start_ts = time.time()
        try:
            response = _post_tool(
                f"{self.base_url}/tools/invoke",
                tool_name,
                args,
                headers,
                timeout=self.timeout_seconds,
            )
            if _should_retry_alias(response, raw_tool):
                retry_tool = _retry_tool_name(raw_tool)
                if retry_tool:
                    response = _post_tool(
                        f"{self.base_url}/tools/invoke",
                        retry_tool,
                        args,
                        headers,
                        timeout=self.timeout_seconds,
                    )
            ok = 200 <= response.status_code < 300
            body = response.text
            log_audit(action_request.action_id, action_request.type, start_ts, ok, "openclaw")
            if not ok:
                return _result(action_request, ok=False, error=f"http_{response.status_code}", output=body)
            return _result(action_request, ok=True, output=body)
        except requests.Timeout:
            log_audit(action_request.action_id, action_request.type, start_ts, False, "openclaw")
            return _result(action_request, ok=False, error="timeout")
        except Exception as exc:
            log_audit(action_request.action_id, action_request.type, start_ts, False, "openclaw")
            return _result(action_request, ok=False, error=f"exception:{exc}")

    def _invoke_github_write(self, action_request: ActionRequest) -> ActionResult:
        if action_request.requires_confirm and not _is_confirmed(action_request):
            return _result(action_request, ok=False, error="confirm_required")

        if not _is_allowlisted("sessions_send", self.allowlist):
            return _result(action_request, ok=False, error="not_allowlisted")

        message = _build_github_message(action_request)
        headers = {"Authorization": f"Bearer {self.token}"}
        args = {
            "sessionKey": self.session_key,
            "timeoutSeconds": self.timeout_seconds,
            "message": message,
        }

        start_ts = time.time()
        try:
            response = _post_tool(
                f"{self.base_url}/tools/invoke",
                "sessions_send",
                args,
                headers,
                timeout=self.timeout_seconds,
            )
            ok = 200 <= response.status_code < 300
            body = response.text
            log_audit(action_request.action_id, action_request.type, start_ts, ok, "openclaw")
            if not ok:
                return _result(action_request, ok=False, error=f"http_{response.status_code}", output=body)
            return _result(action_request, ok=True, output=body)
        except requests.Timeout:
            log_audit(action_request.action_id, action_request.type, start_ts, False, "openclaw")
            return _result(action_request, ok=False, error="timeout")
        except Exception as exc:
            log_audit(action_request.action_id, action_request.type, start_ts, False, "openclaw")
            return _result(action_request, ok=False, error=f"exception:{exc}")


def log_audit(action_id: str, action_type: str, ts: float, ok: bool, provider: str) -> None:
    print(f"[audit] action_id={action_id} type={action_type} provider={provider} ok={ok} ts={ts}")


def _build_github_message(action_request: ActionRequest) -> str:
    cmd = str(action_request.data.get("cmd") or "").strip()
    if cmd:
        return f"Usa la skill github. Ejecuta exactamente este comando gh: {cmd}. Responde SOLO con el JSON crudo."

    intent = str(action_request.data.get("intent") or "").strip()
    if intent:
        return f"Usa la skill github. Ejecuta un comando gh apropiado para: {intent}. Responde SOLO con el JSON crudo."

    return "Usa la skill github. Ejecuta un comando gh apropiado para la solicitud recibida. Responde SOLO con el JSON crudo."


def _load_allowlist() -> dict:
    try:
        data = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {"allowed_tools": [], "tool_aliases": {}}
    return data


def _is_allowlisted(tool_name: str, allowlist: dict) -> bool:
    allowed = allowlist.get("allowed_tools") or []
    return tool_name in set(allowed)


def _raw_tool_name(action_request: ActionRequest) -> str:
    return str(action_request.data.get("tool") or "")


def _resolve_tool_name(action_request: ActionRequest, allowlist: dict) -> str | None:
    raw_tool = _raw_tool_name(action_request)
    if not raw_tool:
        return None
    tool_aliases = allowlist.get("tool_aliases") or {}
    return tool_aliases.get(raw_tool, raw_tool)


def _is_write_action(tool_name: str) -> bool:
    lowered = tool_name.lower()
    return any(token in lowered for token in ("create", "update", "delete", "write"))


def _post_tool(url: str, tool_name: str, args: dict, headers: dict, *, timeout: int) -> requests.Response:
    payload = {
        "tool": tool_name,
        "action": "json",
        "args": args,
    }
    return requests.post(url, json=payload, headers=headers, timeout=timeout)


def _should_retry_alias(response: requests.Response, raw_tool: str) -> bool:
    if response.status_code != 404:
        return False
    body = (response.text or "").lower()
    return any(token in body for token in ("tool not available: github_list", "tool not available: calendar_list")) and bool(raw_tool)


def _retry_tool_name(raw_tool: str) -> str | None:
    lowered = raw_tool.lower()
    if "github" in lowered:
        return "github"
    if "calendar" in lowered:
        return "calendar"
    return None


def _is_confirmed(action_request: ActionRequest) -> bool:
    return bool(action_request.data.get("confirmed") or action_request.data.get("confirm"))


def _result(action_request: ActionRequest, *, ok: bool, error: str | None = None, output: str | None = None) -> ActionResult:
    return ActionResult(
        action_id=action_request.action_id,
        ok=ok,
        output=output,
        error=error,
        provider="openclaw",
        ts=time.time(),
    )
