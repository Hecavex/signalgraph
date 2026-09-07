from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import BoundedSemaphore

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import get_settings

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
# Used for missing/inactive users, so their invalid-login path still verifies a hash.
DUMMY_PASSWORD_HASH = password_hasher.hash("not-a-user-account")
_password_slots = BoundedSemaphore(2)


class PasswordVerificationBusy(RuntimeError):
    pass


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    # Hard process ceiling remains even if a stalled check outlives its Redis lease.
    if not _password_slots.acquire(blocking=False):
        raise PasswordVerificationBusy("Password verification capacity reached")
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
    finally:
        _password_slots.release()


def create_access_token(user_id: str, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": user_id, "role": role, "type": "access", "exp": expires_at, "iat": datetime.now(UTC)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256"), settings.access_token_minutes * 60


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"], options={"require": ["exp", "sub"]})
