from concurrent.futures import ThreadPoolExecutor

import pytest
import redis
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import security
from app.database import Base
from app.models import User
from app.services import login_limits
from app.services.first_owner import create_first_owner


def test_competing_terminal_setup_creates_one_owner(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'first-owner.sqlite'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)

    def setup(number):
        with sessions() as db:
            try:
                create_first_owner(db, f"owner{number}@example.com", "Owner", "StrongPassword2026")
                db.commit()
                return True
            except ValueError:
                db.rollback()
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(setup, [1, 2])) == [False, True]
    with sessions() as db:
        assert db.scalar(select(func.count(User.id))) == 1
    engine.dispose()


def test_unknown_user_still_performs_password_verification(client, monkeypatch):
    checked = []
    monkeypatch.setattr(
        "app.api.auth.verify_password", lambda password, hashed: checked.append(hashed) or False
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": "missing@example.com", "password": "incorrect"}
    )
    assert response.status_code == 401
    assert len(checked) == 1 and checked[0].startswith("$argon2id$")


def test_password_process_ceiling_rejects_without_entering_argon2(monkeypatch):
    calls = []
    monkeypatch.setattr(security.password_hasher.__class__, "verify", lambda *args: calls.append(args))
    assert security._password_slots.acquire(blocking=False)
    assert security._password_slots.acquire(blocking=False)
    try:
        with pytest.raises(security.PasswordVerificationBusy):
            security.verify_password("synthetic", security.DUMMY_PASSWORD_HASH)
        assert calls == []
    finally:
        security._password_slots.release()
        security._password_slots.release()


def test_redis_outage_refuses_authentication_before_verification(monkeypatch):
    class Unavailable:
        def eval(self, *args):
            raise redis.ConnectionError("synthetic unavailable")

    monkeypatch.setattr(login_limits, "auth_store", lambda: Unavailable())
    with pytest.raises(HTTPException) as caught:
        login_limits.reserve_login("account@example.com")
    assert caught.value.status_code == 503


def test_distributed_rejection_is_bounded_and_opaque(monkeypatch):
    calls = []

    class Rejected:
        def eval(self, *args):
            calls.append(args)
            return [0, 31]

    monkeypatch.setattr(login_limits, "auth_store", lambda: Rejected())
    with pytest.raises(HTTPException) as caught:
        login_limits.reserve_login("account@example.com")
    assert caught.value.status_code == 429
    assert caught.value.headers == {"Retry-After": "31"}
    assert "account@example.com" not in str(calls)


def test_success_and_failure_accounting_and_casefolded_key(monkeypatch):
    calls = []

    class Available:
        def eval(self, *args):
            calls.append(args)
            return [1, 0] if args[0] == login_limits.RESERVE else 1

    monkeypatch.setattr(login_limits, "auth_store", lambda: Available())
    first = login_limits.reserve_login("ACCOUNT@example.com")
    second = login_limits.reserve_login("account@example.com")
    assert first[0] == second[0] and first[1] != second[1]
    login_limits.finish_login(first, False)
    login_limits.finish_login(second, True)
    assert calls[-2][-2] == "failure" and calls[-1][-2] == "success"
