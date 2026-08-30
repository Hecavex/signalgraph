from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.database import get_db
from app.deps import require_admin, require_analyst
from app.models import AuditLog, CollectorConfig, Job, User
from app.schemas import CollectorConfigOut, CollectorConfigUpdate, JobOut
from app.services.enrichment import applicable_collectors, ensure_collectors
from app.tasks import enrich_task

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/collectors", response_model=list[CollectorConfigOut])
def collectors(_: User = Depends(require_analyst), db: Session = Depends(get_db)) -> list[CollectorConfig]:
    ensure_collectors(db)
    db.commit()
    return list(db.scalars(select(CollectorConfig).order_by(CollectorConfig.name)).all())


@router.patch("/collectors/{name}", response_model=CollectorConfigOut)
def update_collector(
    name: str,
    payload: CollectorConfigUpdate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CollectorConfig:
    ensure_collectors(db)
    config = db.scalar(select(CollectorConfig).where(CollectorConfig.name == name))
    if config is None:
        raise HTTPException(status_code=404, detail="Collector not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(config, key, value)
    record_audit(db, "collector.update", "collector", config.id, actor, request, {"fields": sorted(changes)})
    db.commit()
    return config


@router.get("/jobs", response_model=list[JobOut])
def jobs(
    failed_only: bool = False,
    _: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> list[Job]:
    query = select(Job)
    if failed_only:
        query = query.where(Job.status.in_(["failed", "partial"]))
    return list(db.scalars(query.order_by(Job.created_at.desc()).limit(200)).all())


@router.post("/jobs/{job_id}/retry", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def retry_job(
    job_id: str,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Job:
    original = db.get(Job, job_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Job not found")
    entity_type = original.result.get("entity_type")
    collectors = applicable_collectors(db, entity_type, original.result.get("collectors_requested"))
    retry = Job(
        collector=original.collector,
        observable=original.observable,
        created_by=actor.id,
        result={"entity_type": entity_type, "retry_of": original.id, "collectors_requested": collectors},
    )
    db.add(retry)
    db.flush()
    record_audit(db, "job.retry", "job", retry.id, actor, request, {"original": original.id})
    db.commit()
    result = enrich_task.delay(retry.id, collectors)
    retry.task_id = result.id
    db.commit()
    return retry


@router.get("/audit")
def audit_log(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)).all()
    return [
        {
            "id": row.id,
            "actor_id": row.actor_id,
            "action": row.action,
            "object_type": row.object_type,
            "object_id": row.object_id,
            "ip_address": row.ip_address,
            "details": row.details,
            "created_at": row.created_at,
        }
        for row in rows
    ]
