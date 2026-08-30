from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record_audit(
    db: Session,
    action: str,
    object_type: str,
    object_id: str | None = None,
    actor: User | None = None,
    request: Request | None = None,
    details: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        object_type=object_type,
        object_id=object_id,
        ip_address=request.client.host if request and request.client else None,
        details=details or {},
    )
    db.add(entry)
    return entry
