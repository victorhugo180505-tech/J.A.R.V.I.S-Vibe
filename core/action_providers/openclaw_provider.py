from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

from core.actions_contract import ActionRequest, ActionResult


ALLOWLIST_PATH = Path(__file__).with_name("openclaw_allowlist.json")
DEFAULT_BASE_URL = "http://127.0.0.1:28789"
TIMEOUT_SECONDS = 10


class OpenClawProvider:
    def __init__(self) -> None:
        self.base_url = os.getenv("OPENCLOW_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.token = os.getenv("OPENCLAW_GATEWAY_TOKEN")
        if not self.token:
            raise ValueError("OPENCLAW_GATEWAY_TOKEN is required")
        self.allowlist = _load_allowlist()

    def invoke(self, action_request: ActionRequest) -> ActionResult:
        tool_name = _resolve_tool_name(action_request, self.allowlist)
        if not tool_name:
            return _result(action_request, ok=False, error="missing_tool")

        if not _is_allowlisted(tool_name, self.allowlist):
            return _result(action_request, ok=False, error="not_allowlisted")

        if _is_write_action(tool_name) and not _is_confirmed(action_request):
            return _result(action_request, ok=False, error="confirm_required")

        url = f"{self.base_url}/tools/invoke"
        payload = {
            "tool": tool_name,
            "action": "json",
            "args": action_request.data.get("args", {}),
        }
        headers = {"Authorization": f"Bearer {self.token}"}

        start_ts = time.time()
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
            ok = response.status_code >= 200 and response.status_code < 300
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


def _load_allowlist() -> dict:
    try:
        data = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {"allowed_tools": [], "tool_aliases": {}}
    return data


def _is_allowlisted(tool_name: str, allowlist: dict) -> bool:
    allowed = allowlist.get("allowed_tools") or []
    return tool_name in set(allowed)


def _resolve_tool_name(action_request: ActionRequest, allowlist: dict) -> str | None:
    raw_tool = action_request.data.get("tool")
    if not raw_tool:
        return None
    tool_aliases = allowlist.get("tool_aliases") or {}
    return tool_aliases.get(raw_tool, raw_tool)


def _is_write_action(tool_name: str) -> bool:
    lowered = tool_name.lower()
    return any(token in lowered for token in ("create", "update", "delete", "write"))


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
