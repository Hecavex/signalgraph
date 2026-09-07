"""Create disposable configuration only on a GitHub-hosted CI runner."""

import os
import secrets
from pathlib import Path


def configuration():
    database_password = secrets.token_hex(24)
    password = secrets.token_urlsafe(32)
    values = {
        "SECRET_KEY": secrets.token_urlsafe(48),
        "POSTGRES_DB": "signalgraph",
        "POSTGRES_USER": "signalgraph",
        "POSTGRES_PASSWORD": database_password,
        "DATABASE_URL": f"postgresql+psycopg://signalgraph:{database_password}@postgres:5432/signalgraph",
        "REDIS_URL": "redis://redis:6379/0",
        "ENVIRONMENT": "production",
        "AUTO_CREATE_TABLES": "false",
        "CORS_ORIGINS": "http://127.0.0.1:8080",
        "URLSCAN_API_KEY": "",
        "DEMO_ADMIN_PASSWORD": password,
    }
    return values, password


def main():
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
    ):
        raise SystemExit("This bootstrap is restricted to disposable GitHub-hosted runners")
    values, password = configuration()
    for key in ("SECRET_KEY", "POSTGRES_PASSWORD", "DEMO_ADMIN_PASSWORD"):
        print(f"::add-mask::{values[key]}")
    # Exclusive creation prevents replacing an operator's existing configuration.
    with Path(".env").open("x", encoding="utf-8") as output:
        output.write("".join(f"{key}={value}\n" for key, value in values.items()))
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as output:
        output.write(f"E2E_PASSWORD={password}\n")
    print("Disposable synthetic configuration created")


if __name__ == "__main__":
    main()
