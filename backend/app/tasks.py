from __future__ import annotations

from sqlalchemy import select

from app.celery_app import celery
from app.database import SessionLocal
from app.models import CollectorConfig
from app.services.enrichment import ensure_collectors, run_job


@celery.task(
    name="signalgraph.enrich", bind=True, autoretry_for=(RuntimeError,), retry_backoff=True, max_retries=2
)
def enrich_task(self, job_id: str, collectors: list[str]) -> dict:
    with SessionLocal() as db:
        return run_job(db, job_id, collectors)


@celery.task(name="signalgraph.collector_health")
def collector_health() -> dict:
    with SessionLocal() as db:
        ensure_collectors(db)
        db.commit()
        return {
            item.name: {"enabled": item.enabled, "last_error": item.last_error}
            for item in db.scalars(select(CollectorConfig)).all()
        }
