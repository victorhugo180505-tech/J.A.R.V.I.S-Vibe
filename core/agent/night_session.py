from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import uuid


STATUSES = {
    "PLANNING",
    "AWAITING_CONFIRM",
    "RUNNING",
    "DONE",
    "CANCELLED",
    "TIMED_OUT",
}


@dataclass
class NightSession:
    session_id: str
    created_at: datetime
    expires_at: datetime
    scope: set[str]
    max_minutes: int = 60
    status: str = "PLANNING"
    objective: str = ""
    plan: list[str] = field(default_factory=list)

    @classmethod
    def create(cls, objective: str, scope: set[str], max_minutes: int = 60) -> "NightSession":
        now = datetime.now(timezone.utc)
        session_id = uuid.uuid4().hex[:8]
        expires_at = now + timedelta(minutes=max_minutes)
        return cls(
            session_id=session_id,
            created_at=now,
            expires_at=expires_at,
            scope=scope,
            max_minutes=max_minutes,
            status="PLANNING",
            objective=objective,
        )

    def start(self) -> None:
        if self.status not in {"PLANNING", "AWAITING_CONFIRM"}:
            return
        self.status = "RUNNING"

    def cancel(self) -> None:
        if self.status in {"DONE", "CANCELLED", "TIMED_OUT"}:
            return
        self.status = "CANCELLED"

    def is_active(self) -> bool:
        if self.status == "CANCELLED":
            return False
        if datetime.now(timezone.utc) >= self.expires_at:
            self.status = "TIMED_OUT"
            return False
        return self.status in {"RUNNING", "AWAITING_CONFIRM"}

    def remaining_seconds(self) -> int:
        remaining = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining))
