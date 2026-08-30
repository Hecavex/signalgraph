from conftest import create_user


def test_first_admin_bootstrap_and_login(client):
    status = client.get("/api/v1/auth/status")
    assert status.status_code == 200
    assert status.json() == {"bootstrap_required": True}

    created = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "first@example.com",
            "display_name": "First Admin",
            "password": "CorrectHorse2026",
            "role": "viewer",
        },
    )
    assert created.status_code == 201
    assert created.json()["user"]["role"] == "admin"
    assert client.get("/api/v1/auth/status").json() == {"bootstrap_required": False}

    duplicate = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "second@example.com",
            "display_name": "Second Admin",
            "password": "CorrectHorse2026",
            "role": "admin",
        },
    )
    assert duplicate.status_code == 409

    rejected = client.post(
        "/api/v1/auth/login",
        json={"email": "first@example.com", "password": "incorrect-password"},
    )
    assert rejected.status_code == 401


def test_role_enforcement(client, admin):
    viewer = create_user(client, admin, "viewer@example.com", "viewer")
    analyst = create_user(client, admin, "analyst@example.com", "analyst")

    assert client.get("/api/v1/entities", headers=viewer["headers"]).status_code == 200
    denied = client.post(
        "/api/v1/entities",
        headers=viewer["headers"],
        json={"value": "example.org"},
    )
    assert denied.status_code == 403
    allowed = client.post(
        "/api/v1/entities",
        headers=analyst["headers"],
        json={"value": "example.org"},
    )
    assert allowed.status_code == 201
    assert client.get("/api/v1/auth/users", headers=analyst["headers"]).status_code == 403
    assert client.get("/api/v1/auth/users", headers=admin["headers"]).status_code == 200
