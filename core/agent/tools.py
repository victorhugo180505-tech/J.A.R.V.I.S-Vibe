from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import subprocess
import sys


ALLOWED_PYTEST_ARGS = {
    "-q",
    "tests",
    "-m",
    "contract",
    "vtube",
    "integration",
}


@dataclass
class ToolResult:
    ok: bool
    output: str


def run_pytest(selected_args: list[str]) -> ToolResult:
    args = [arg for arg in selected_args if arg in ALLOWED_PYTEST_ARGS]
    cmd = [sys.executable, "-m", "pytest"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        output = (result.stdout or "") + (result.stderr or "")
        return ToolResult(ok=result.returncode == 0, output=output.strip())
    except Exception as exc:
        return ToolResult(ok=False, output=f"pytest failed: {exc}")


def grep_repo(query: str, root: str = ".") -> ToolResult:
    root_path = Path(root)
    matches: list[str] = []
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if query in text:
            matches.append(str(path))
    output = "\n".join(matches) if matches else ""
    return ToolResult(ok=True, output=output)


def list_files(paths: list[str]) -> ToolResult:
    listed: list[str] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for child in path.iterdir():
                listed.append(str(child))
        elif path.exists():
            listed.append(str(path))
    return ToolResult(ok=True, output="\n".join(listed))


def write_report(path: str, content: str) -> ToolResult:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8")
    return ToolResult(ok=True, output=str(report_path))
