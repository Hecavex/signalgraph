"""Real PostgreSQL setup concurrency test. Only for an empty disposable CI stack."""

import os
from concurrent.futures import ThreadPoolExecutor

from app.database import SessionLocal, engine
from app.models import User
from app.services.first_owner import create_first_owner
from sqlalchemy import func, select


def main():
    if os.environ.get("SIGNALGRAPH_DISPOSABLE_CI") != "true":
        raise SystemExit("Refusing non-disposable setup test")
    if engine.dialect.name != "postgresql":
        raise SystemExit("This gate requires real PostgreSQL")
    with SessionLocal() as db:
        if db.scalar(select(func.count(User.id))) != 0:
            raise SystemExit("Refusing setup test on a nonempty user table")

    def create():
        with SessionLocal() as db:
            try:
                create_first_owner(
                    db, os.environ["E2E_EMAIL"], "Synthetic CI owner", os.environ["E2E_PASSWORD"]
                )
                db.commit()
                return "created"
            except ValueError:
                db.rollback()
                return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert sorted(results) == ["created", "rejected"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count(User.id))) == 1
    print("Concurrent PostgreSQL setup produced exactly one synthetic owner")


if __name__ == "__main__":
    main()
