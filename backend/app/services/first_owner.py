from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.models import User
from app.security import hash_password


def create_first_owner(db: Session, email: str, display_name: str, password: str) -> User:
    """Terminal-only first ownership. Call with a fresh session, commit on success."""
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        # Serialize competing terminal setup commands across processes.
        db.execute(text("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"))
    elif dialect == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        raise ValueError("First-owner setup supports PostgreSQL and SQLite only")
    if db.scalar(select(func.count(User.id))):
        raise ValueError("An owner already exists. Use authenticated user administration.")
    user = User(
        email=email.lower(),
        display_name=display_name,
        password_hash=hash_password(password),
        role="admin",
    )
    db.add(user)
    db.flush()
    record_audit(db, "auth.bootstrap_cli", "user", user.id, user)
    return user
