from __future__ import annotations

import os

os.environ.update(
    {
        "DATABASE_URL": "sqlite://",
        "SECRET_KEY": "test-secret-key-that-is-long-enough-for-tests",
        "AUTO_CREATE_TABLES": "true",
        "CELERY_TASK_ALWAYS_EAGER": "true",
        "REDIS_URL": "redis://localhost:6399/15",
        "ENVIRONMENT": "test",
    }
)

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin(client):
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "admin@example.com",
            "display_name": "Admin Analyst",
            "password": "StrongPassword2026",
            "role": "viewer",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {"headers": {"Authorization": f"Bearer {body['access_token']}"}, "user": body["user"]}


def create_user(client, admin, email: str, role: str) -> dict:
    response = client.post(
        "/api/v1/auth/users",
        headers=admin["headers"],
        json={
            "email": email,
            "display_name": role.title(),
            "password": "StrongPassword2026",
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPassword2026"})
    assert login.status_code == 200
    return {"headers": {"Authorization": f"Bearer {login.json()['access_token']}"}, "user": response.json()}
