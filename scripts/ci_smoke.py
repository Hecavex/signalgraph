"""Exercise the existing v1 API on an isolated local Compose instance."""

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request(path, payload=None, token=None, expected=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    call = Request(f"http://127.0.0.1:8000{path}", data=data, headers=headers)
    try:
        response = urlopen(call, timeout=10)  # noqa: S310 - fixed loopback CI service, not user input
    except HTTPError as error:
        response = error
    with response:
        if response.status != expected:
            raise AssertionError(f"{path}: HTTP {response.status}, expected {expected}")
        return json.loads(response.read(1_000_000))


def main():
    ready = request("/health/ready")
    assert ready == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}
    assert request("/api/v1/auth/status")["bootstrap_required"] is False
    credentials = {"email": os.environ["E2E_EMAIL"], "password": os.environ["E2E_PASSWORD"]}
    request("/api/v1/auth/login", {**credentials, "password": "incorrect-synthetic-password"}, expected=401)
    request("/api/v1/entities", expected=401)
    request("/api/v1/auth/bootstrap", {**credentials, "display_name": "CI", "role": "admin"}, expected=410)
    token = request("/api/v1/auth/login", credentials)["access_token"]
    assert request("/api/v1/auth/me", token=token)["role"] == "admin"
    records = request("/api/v1/entities?q=northstar", token=token)
    assert records["total"] >= 2
    failed = {"email": "rate-limit-synthetic@example.com", "password": "incorrect-synthetic-password"}
    for _ in range(8):
        request("/api/v1/auth/login", failed, expected=401)
    request("/api/v1/auth/login", failed, expected=429)
    # Account isolation: the real synthetic administrator is not locked by failures
    # on another account. This exercises the real Redis Lua accounting, not mocks.
    request("/api/v1/auth/login", credentials)
    print("Readiness, first-run lockout, authentication and synthetic search passed")


if __name__ == "__main__":
    main()
