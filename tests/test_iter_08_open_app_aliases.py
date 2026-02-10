from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from actions.open_app import open_app, resolve_app_name


def test_resolve_bloc_de_notas():
    assert resolve_app_name("bloc de notas") == "notepad"


def test_spotify_allowed(monkeypatch):
    called = {}

    def fake_popen(cmd, shell=True):
        called["cmd"] = cmd
        called["shell"] = shell

    monkeypatch.setattr("actions.open_app.subprocess.Popen", fake_popen)

    open_app("spotify")
    assert called["cmd"] == "spotify"
