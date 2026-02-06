# ai/openai_oauth.py
import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Union

CODEX_MODEL_CHAT = os.getenv("CODEX_MODEL_CHAT", "gpt-5.2")
CODEX_MODEL_CODE = os.getenv("CODEX_MODEL_CODE", "gpt-5.2-codex")
CODEX_CLI_PWSH = os.getenv("CODEX_CLI_PWSH", r"C:\Users\victo\AppData\Roaming\npm\codex.ps1")

def _infer_codex_js_from_ps1(ps1_path: str) -> Path:
    basedir = Path(ps1_path).resolve().parent
    js = basedir / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    if not js.exists():
        raise FileNotFoundError(f"No encontré codex.js en: {js}")
    return js

def _extract_last_assistant_message(stdout: str) -> str:
    if not stdout:
        return ""

    # Normaliza saltos
    s = stdout.replace("\r\n", "\n")

    # Caso típico: ... \nassistant\n<contenido>
    markers = list(re.finditer(r"\nassistant\s*\n", s, flags=re.IGNORECASE))
    if markers:
        return s[markers[-1].end():].strip()

    # Fallback: a veces viene "assistant:" o similar
    markers2 = list(re.finditer(r"\nassistant\s*:\s*", s, flags=re.IGNORECASE))
    if markers2:
        return s[markers2[-1].end():].strip()

    return s.strip()

def ask_openai_oauth(
    messages: List[Dict],
    task_type: str = "general",
    return_meta: bool = False,
) -> Union[str, Tuple[str, str]]:
    model = CODEX_MODEL_CODE if task_type == "code" else CODEX_MODEL_CHAT

    prompt_lines = []
    for msg in messages:
        role = (msg.get("role") or "").strip().lower()
        content = (msg.get("content") or "").strip()
        if not content:
            continue

        # Evita caracteres problemáticos Windows
        content = content.replace("→", "->")

        if role == "system":
            prompt_lines.append(f"SYSTEM:\n{content}\n")
        elif role == "user":
            prompt_lines.append(f"USER:\n{content}\n")
        else:
            prompt_lines.append(f"ASSISTANT:\n{content}\n")

    prompt = "\n".join(prompt_lines).strip()

    codex_js = _infer_codex_js_from_ps1(CODEX_CLI_PWSH)

    cmd = ["node", str(codex_js), "exec", "--model", model]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    p = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=os.getcwd(),
        env=env,
        timeout=120,
    )

    if p.returncode != 0:
        raise RuntimeError(
            "Codex exec falló.\n"
            f"ReturnCode={p.returncode}\n"
            f"STDERR:\n{p.stderr}\n"
            f"STDOUT:\n{p.stdout}\n"
        )

    last = _extract_last_assistant_message(p.stdout)
    if not last:
        last = (p.stdout or "").strip()

    return (last, model) if return_meta else last
