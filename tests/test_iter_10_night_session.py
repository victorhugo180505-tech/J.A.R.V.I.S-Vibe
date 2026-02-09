from datetime import datetime, timedelta, timezone

from core.agent.night_session import NightSession
from core.agent import tools as night_tools


def test_night_session_lifecycle():
    session = NightSession.create("objetivo", scope={"research_repo"})
    assert session.status == "PLANNING"
    session.start()
    assert session.status == "RUNNING"
    assert session.is_active() is True
    session.cancel()
    assert session.status == "CANCELLED"
    assert session.is_active() is False


def test_night_session_timeout():
    session = NightSession.create("objetivo", scope=set(), max_minutes=1)
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert session.is_active() is False
    assert session.status == "TIMED_OUT"


def test_write_report_contains_headers(tmp_path):
    report_path = tmp_path / "night.md"
    content = "\n".join([
        "# NightSession demo",
        "",
        "**Objetivo:** demo",
        "",
        "## Plan",
        "- [ ] item",
        "",
        "## Acciones realizadas",
        "- action",
        "",
        "## Resultado pytest",
        "```",
        "ok",
        "```",
        "",
        "## Riesgos/Pendientes",
        "- pendiente",
    ])
    result = night_tools.write_report(str(report_path), content)
    assert result.ok is True
    written = report_path.read_text(encoding="utf-8")
    assert "# NightSession" in written
    assert "## Plan" in written
    assert "## Resultado pytest" in written
