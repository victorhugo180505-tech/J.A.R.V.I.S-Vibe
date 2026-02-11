from __future__ import annotations

CODE_HINTS = [
    "error", "exception", "traceback", "stack", "stacktrace", "segfault", "core dumped",
    "compile", "compila", "compilación", "linker", "undefined reference", "ld:",
    "python", "c++", "cpp", "java", "javascript", "typescript", "node", "npm", "pip",
    "leetcode", "codeforces", "icpc", "algoritmo", "complexity", "big-o", "dp", "graph",
    "bug", "fix", "refactor", "regex", "sql", "api", "endpoint", "docker", "wsl",
    "pr", "pull request", "commit",
    "gh ", "git ",
    "```", "class ", "def ", "import ", "#include", "int main", "std::", "public static",
]


def detect_task_type(user_text: str) -> str:
    t = (user_text or "").strip()
    low = t.lower()

    if low.startswith("/code "):
        return "code"
    if low == "/code":
        return "code"
    if low.startswith("/chat "):
        return "general"
    if low == "/chat":
        return "general"

    for k in CODE_HINTS:
        if k in low:
            return "code"
    return "general"


def strip_force_prefix(user_text: str) -> str:
    t = (user_text or "").strip()
    low = t.lower()
    if low.startswith("/code "):
        return t[6:].strip()
    if low.startswith("/chat "):
        return t[6:].strip()
    if low in {"/code", "/chat"}:
        return ""
    return user_text
