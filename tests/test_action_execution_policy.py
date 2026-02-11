from core.action_execution_policy import should_dispatch_action


def test_none_action_not_dispatched():
    assert should_dispatch_action("none") is False


def test_non_none_action_dispatched():
    assert should_dispatch_action("github_write") is True
