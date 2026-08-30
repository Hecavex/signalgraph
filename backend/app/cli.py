from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import redis
import typer
from rich.console import Console
from sqlalchemy import func, select, text

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password
from app.seed import seed_demo
from app.services.enrichment import ensure_collectors

cli = typer.Typer(help="SignalGraph operational commands", no_args_is_help=True)
console = Console()


@cli.command()
def doctor() -> None:
    """Check configuration, database, Redis, and collector initialization."""
    settings = get_settings()
    checks: list[tuple[str, bool, str]] = []
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks.append(("database", True, settings.database_url.split("@")[-1]))
    except Exception as exc:
        checks.append(("database", False, f"{type(exc).__name__}: {exc}"))
    try:
        redis.from_url(settings.redis_url, socket_connect_timeout=2).ping()
        checks.append(("redis", True, settings.redis_url.split("@")[-1]))
    except Exception as exc:
        checks.append(("redis", False, f"{type(exc).__name__}: {exc}"))
    try:
        with SessionLocal() as db:
            ensure_collectors(db)
            db.commit()
        checks.append(("collectors", True, "configuration available"))
    except Exception as exc:
        checks.append(("collectors", False, f"{type(exc).__name__}: {exc}"))
    for name, passed, detail in checks:
        console.print(f"[{'green' if passed else 'red'}]{'PASS' if passed else 'FAIL'}[/] {name}: {detail}")
    if not all(item[1] for item in checks):
        raise typer.Exit(1)


@cli.command("create-admin")
def create_admin(
    email: str = typer.Option(..., prompt=True),
    display_name: str = typer.Option("Administrator"),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
) -> None:
    """Create a local administrator without exposing a public bootstrap endpoint."""
    if len(password) < 12:
        raise typer.BadParameter("Password must be at least 12 characters")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email.lower())):
            raise typer.BadParameter("Email already exists")
        db.add(
            User(
                email=email.lower(),
                display_name=display_name,
                password_hash=hash_password(password),
                role="admin",
            )
        )
        db.commit()
    console.print(f"[green]Created administrator[/] {email.lower()}")


@cli.command("seed-demo")
def seed_demo_command(
    email: str = typer.Option("admin@example.com"),
    password: str = typer.Option("SignalGraph!2026", envvar="DEMO_ADMIN_PASSWORD", hide_input=True),
) -> None:
    """Load a clearly labeled synthetic investigation dataset."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        result = seed_demo(db, email, password)
    console.print(
        f"[green]Demo dataset ready[/]: {result['entities']} entities, admin {result['admin_email']}"
    )


def _postgres_args(database_url: str) -> tuple[list[str], dict[str, str]]:
    parsed = urlsplit(database_url.replace("postgresql+psycopg://", "postgresql://"))
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise typer.BadParameter("This operation requires PostgreSQL or a SQLite database file")
    args = [
        "--host",
        parsed.hostname or "localhost",
        "--port",
        str(parsed.port or 5432),
        "--username",
        parsed.username or "postgres",
        "--dbname",
        parsed.path.lstrip("/"),
    ]
    environment = os.environ.copy()
    if parsed.password:
        environment["PGPASSWORD"] = parsed.password
    return args, environment


@cli.command()
def backup(output: Path = typer.Argument(...)) -> None:
    """Create a PostgreSQL custom dump or a consistent SQLite copy."""
    settings = get_settings()
    destination = output.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if settings.database_url.startswith("sqlite"):
        source = Path(settings.database_url.split("///", 1)[-1]).resolve()
        if not source.is_file():
            raise typer.BadParameter(f"SQLite database does not exist: {source}")
        shutil.copy2(source, destination)
    else:
        args, environment = _postgres_args(settings.database_url)
        subprocess.run(
            ["pg_dump", *args, "--format=custom", "--file", str(destination)], check=True, env=environment
        )
    console.print(f"[green]Backup created[/] {destination}")


@cli.command()
def restore(backup_file: Path, confirm: bool = typer.Option(False, "--confirm")) -> None:
    """Restore a backup. Requires --confirm because current data is replaced."""
    if not confirm:
        raise typer.BadParameter("Restore replaces current data; pass --confirm after making a backup")
    source = backup_file.expanduser().resolve()
    if not source.is_file():
        raise typer.BadParameter(f"Backup does not exist: {source}")
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        destination = Path(settings.database_url.split("///", 1)[-1]).resolve()
        if destination.parent != source.parent and not destination.parent.exists():
            destination.parent.mkdir(parents=True)
        shutil.copy2(source, destination)
    else:
        args, environment = _postgres_args(settings.database_url)
        subprocess.run(
            ["pg_restore", *args, "--clean", "--if-exists", "--no-owner", str(source)],
            check=True,
            env=environment,
        )
    console.print("[green]Restore completed[/]")


@cli.command("stats")
def stats() -> None:
    """Show a compact local deployment summary."""
    with SessionLocal() as db:
        console.print(f"Users: {db.scalar(select(func.count(User.id))) or 0}")


if __name__ == "__main__":
    cli()
