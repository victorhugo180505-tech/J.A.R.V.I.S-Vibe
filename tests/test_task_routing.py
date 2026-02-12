from core.task_routing import detect_task_type
from core.local_intents import detect_intent
from core.github_followups import build_cached_repos_response


def test_detect_task_type_github_followup_is_general():
    assert detect_task_type("dime nombres de repositorios de github") == "general"


def test_detect_task_type_private_followup_is_general():
    assert detect_task_type("solo dime los privados") == "general"


def test_detect_task_type_gh_command_is_code():
    assert detect_task_type("ejecuta gh repo list --limit 200 --json name,visibility") == "code"


def test_local_intent_github_cached_names_followup():
    action = detect_intent("dime los nombres de mis repos")
    assert action is not None
    assert action.type == "none"
    assert action.data.get("kind") == "github_cached_names"


def test_local_intent_github_cached_private_followup():
    action = detect_intent("dime los privados de mis repos")
    assert action is not None
    assert action.type == "none"
    assert action.data.get("kind") == "github_cached_visibility"
    assert action.data.get("visibility") == "PRIVATE"


def test_local_intent_repo_list_private_uses_visibility_cmd():
    action = detect_intent("lista mis repos privados")
    assert action is not None
    assert action.type == "github_write"
    assert "--visibility private" in (action.data.get("cmd") or "")


def test_cached_private_followup_response_without_openclaw():
    items = [
        {"name": "repo-public", "visibility": "PUBLIC"},
        {"name": "repo-private", "visibility": "PRIVATE"},
    ]
    names = ["repo-public", "repo-private"]
    speech, verbose = build_cached_repos_response(items, names, "PRIVATE")
    assert "repo-private" in speech
    assert "repo-private" in verbose
    assert "repo-public" not in verbose
