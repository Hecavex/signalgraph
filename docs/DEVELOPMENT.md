# Development

## Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r backend/requirements-build.lock -r backend/requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e ".\backend[dev]"
$env:DATABASE_URL = "sqlite:///./signalgraph-dev.db"
$env:SECRET_KEY = "local-development-secret-change-before-production"
$env:AUTO_CREATE_TABLES = "true"
$env:CELERY_TASK_ALWAYS_EAGER = "true"
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

SQLite is permitted only for development, isolated tests, and screenshots. PostgreSQL is the supported deployment database.

## Frontend

```powershell
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
.\.venv\Scripts\ruff.exe check backend
cd frontend
npm test
npm run build
```

Or use `scripts/verify.ps1` after installing all dependencies.

## Migrations

```powershell
cd backend
..\.venv\Scripts\alembic.exe upgrade head
..\.venv\Scripts\alembic.exe revision --autogenerate -m "describe change"
```

Review generated migrations before committing. Never use `Base.metadata.create_all` as a production migration path.

## Reviewed dependency set

`pyproject.toml` declares supported ranges. The committed `requirements.lock` is the exact runtime set. `requirements-dev.lock` includes the development tools with matching runtime versions, and `requirements-build.lock` fixes the build tooling. CI and the production Dockerfile install these hashes before installing the local project with dependency resolution and build isolation disabled.

Update the locks intentionally with uv 0.12.5, then review the diff and run all tests. Ordinary builds do not regenerate them.

```powershell
python -m uv pip compile backend/pyproject.toml --universal --python-version 3.12 --generate-hashes -o backend/requirements.lock
python -m uv pip compile backend/pyproject.toml --extra dev --universal --python-version 3.12 --generate-hashes -c backend/requirements.lock -o backend/requirements-dev.lock
python -m uv pip compile backend/requirements-build.in --universal --python-version 3.12 --generate-hashes -c backend/requirements-dev.lock -o backend/requirements-build.lock
python -m unittest discover -s scripts -p "test_ci_*.py"
```

An existing uv output retains its pins. Add `--upgrade-package NAME` to the relevant command for a targeted maintenance update, or `--upgrade` for a deliberately reviewed whole-set update. Never use dependency overrides to hide an incompatible resolution. Hash validation rejects different distribution bytes, not vulnerabilities. Review security advisories separately.

See the upstream [uv locking documentation](https://docs.astral.sh/uv/pip/compile/) and [pip hash-checking guidance](https://pip.pypa.io/en/stable/topics/secure-installs/). These locks cover Python packages, not immutable base-image or OS package digests. The supported runtime remains Python 3.12 in the reference Linux containers.

## Recurring v1 runtime assurance

The existing `containers` required CI job now boots PostgreSQL, Redis, API, worker, scheduler and frontend in a unique disposable Compose project. It checks the real Alembic revision and empty user table before seeding anything, creates an administrator through the CLI, checks authentication failures and bootstrap lockout, and exercises the existing three analyst workflows with the synthetic Northstar dataset. A real Celery queue round trip checks worker execution without querying external intelligence providers.

The job is limited to 25 minutes with a 180-second service health wait. Weekly scheduling repeats the same gate without declaring a release. Configuration is generated exclusively on GitHub-hosted runners, uses random disposable secrets, and cannot overwrite an existing `.env`. No production database, provider keys or analyst records are used.

Only an allowlisted service-health JSON and failed-test screenshots from synthetic data are retained for seven days. Authenticated Playwright traces, raw container logs, environment files and response tokens are not uploaded. Do not copy this diagnostic policy to a real analyst environment without a separate privacy review.

A successful container build alone is not runtime verification. The hosted runtime job must pass for the exact revision. Local Docker unavailability must be reported as a local verification limit, not replaced by a success claim. This recurring gate preserves v1 and neither tags stable v1.0.0 nor activates v2-v5. Backup/restore and upgrade rehearsals remain part of an explicit release audit.
