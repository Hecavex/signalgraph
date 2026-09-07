from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.database import get_db
from app.deps import current_user, require_admin
from app.models import User
from app.schemas import AuthStatus, LoginRequest, TokenResponse, UserCreate, UserOut
from app.security import (
    DUMMY_PASSWORD_HASH,
    PasswordVerificationBusy,
    create_access_token,
    hash_password,
    verify_password,
)
from app.services.login_limits import finish_login, reserve_login

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/status", response_model=AuthStatus)
def auth_status(db: Session = Depends(get_db)) -> AuthStatus:
    return AuthStatus(bootstrap_required=(db.scalar(select(func.count(User.id))) or 0) == 0)


@router.post("/bootstrap", status_code=status.HTTP_410_GONE)
def bootstrap_admin() -> None:
    # A reachable web application must not grant first ownership to its first visitor.
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Web setup is disabled. Run signalgraph create-admin in the deployment terminal.",
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    reservation = reserve_login(str(payload.email))
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    valid = False
    try:
        checked = verify_password(
            payload.password,
            user.password_hash if user is not None and user.is_active else DUMMY_PASSWORD_HASH,
        )
        valid = user is not None and user.is_active and checked
    except PasswordVerificationBusy as exc:
        raise HTTPException(
            429, "Authentication is busy. Try again shortly.", headers={"Retry-After": "1"}
        ) from exc
    finally:
        finish_login(reservation, valid)
    if not valid:
        record_audit(db, "auth.login_failed", "user", details={"email": str(payload.email)}, request=request)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    user.last_login_at = datetime.now(UTC)
    record_audit(db, "auth.login", "user", user.id, user, request)
    db.commit()
    token, expires_in = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())).all())


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    user = User(
        email=email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()
    record_audit(db, "user.create", "user", user.id, actor, request, {"role": user.role})
    db.commit()
    return user
