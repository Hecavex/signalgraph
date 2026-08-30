# Development

## Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
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
