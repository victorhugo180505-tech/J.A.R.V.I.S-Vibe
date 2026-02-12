import subprocess

# Lista blanca de apps permitidas
ALLOWED_APPS = {
    "notepad": "notepad",
    "spotify": "spotify",
    "calc": "calc",
    "calculator": "calc",
    "explorer": "explorer",
    "cmd": "cmd",
}

APP_ALIASES = {
    "bloc de notas": "notepad",
    "notas": "notepad",
    "spotify": "spotify",
}

def resolve_app_name(app_name: str) -> str:
    normalized = (app_name or "").strip().lower()
    return APP_ALIASES.get(normalized, normalized)


def open_app(app_name):
    app_name = resolve_app_name(app_name)

    if app_name not in ALLOWED_APPS:
        raise ValueError(f"App no permitida: {app_name}")

    subprocess.Popen(ALLOWED_APPS[app_name], shell=True)
