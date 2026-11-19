from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditEvent


def log_event(
    db: Session,
    *,
    crew_id: int,
    actor_id: int,
    action: str,
    details: str = "",
) -> None:
    db.add(
        AuditEvent(
            crew_id=crew_id,
            actor_id=actor_id,
            action=action,
            details=details,
        )
    )
