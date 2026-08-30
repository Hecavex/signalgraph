# Installation

SignalGraph v1 is designed for one Docker host controlled by the user.

## Requirements

- Docker Engine 24 or newer
- Docker Compose v2
- 4 GB RAM minimum; 8 GB recommended for sustained collection
- 10 GB available storage plus room for retained intelligence and backups

## Start from a clean clone

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Replace both placeholder passwords and `SECRET_KEY` in `.env`, then start the deployment:

```bash
docker compose up --build -d
docker compose ps
```

Open `http://localhost:8080`. The first-run screen creates the first administrator. The API reference is available locally at `http://localhost:8000/api/docs`.

Alternatively, create the first administrator from the container:

```bash
docker compose exec api signalgraph create-admin
```

## Verify the deployment

```bash
docker compose exec api signalgraph doctor
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

`health/live` confirms the process. `health/ready` also checks PostgreSQL and Redis.

## Optional demo dataset

```bash
docker compose exec api signalgraph seed-demo
```

The demo data is synthetic and clearly labeled. Change `DEMO_ADMIN_PASSWORD` before using the command on an exposed deployment.

## Reverse proxy

Expose the frontend service through a TLS-terminating reverse proxy. Keep PostgreSQL and Redis private. The API is bound to loopback by default; the frontend proxies `/api/` internally.

## Stop

```bash
docker compose down
```

Do not add `--volumes` unless you intentionally want to delete the local database and queue data after verifying a recoverable backup.
