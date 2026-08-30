# Backup and Restore

Back up before upgrades, migration work, or retention changes.

## Create a backup

PowerShell:

```powershell
.\scripts\backup.ps1 -Output C:\backups\signalgraph-2026-08-30.dump
```

Portable shell command:

```bash
docker compose exec -T postgres pg_dump -U signalgraph -d signalgraph -Fc > signalgraph.dump
```

Store the dump outside the Docker host when possible. Protect it as sensitive intelligence.

## Validate a backup

```bash
pg_restore --list signalgraph.dump
```

A backup is not verified until it has been restored into a separate test database and representative entities, investigations, and reports have been checked.

## Restore

Stop API writers and preserve the current database first:

```bash
docker compose stop api worker scheduler
docker compose cp signalgraph.dump postgres:/tmp/signalgraph.dump
docker compose exec postgres pg_restore -U signalgraph -d signalgraph --clean --if-exists --no-owner /tmp/signalgraph.dump
docker compose exec api alembic upgrade head
docker compose start api worker scheduler
docker compose exec api signalgraph doctor
```

Restore replaces current database objects. Review the exact target deployment before running it.
