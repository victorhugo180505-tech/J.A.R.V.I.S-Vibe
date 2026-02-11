from core.task_routing import detect_task_type
from core.local_intents import detect_intent


def test_detect_task_type_github_followup_is_general():
    assert detect_task_type("dime nombres de repositorios de github") == "general"


def test_detect_task_type_gh_command_is_code():
    assert detect_task_type("ejecuta gh repo list --limit 200 --json name,visibility") == "code"


def test_local_intent_github_cached_names_followup():
    action = detect_intent("dime los nombres de mis repos")
    assert action is not None
    assert action.type == "none"
    assert action.data.get("kind") == "github_cached_names"
