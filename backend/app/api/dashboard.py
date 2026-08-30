from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import require_viewer
from app.models import CollectorConfig, Entity, Investigation, Observation, Relationship, User
from app.schemas import DashboardResponse
from app.services.enrichment import ensure_collectors

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(_: User = Depends(require_viewer), db: Session = Depends(get_db)) -> DashboardResponse:
    ensure_collectors(db)
    db.commit()
    by_type = dict(db.execute(select(Entity.type, func.count(Entity.id)).group_by(Entity.type)).all())
    recent_entities = db.scalars(
        select(Entity).options(selectinload(Entity.tags)).order_by(Entity.created_at.desc()).limit(6)
    ).all()
    high_risk = db.scalars(
        select(Entity)
        .options(selectinload(Entity.tags))
        .where(Entity.risk_score >= 50)
        .order_by(Entity.risk_score.desc())
        .limit(6)
    ).all()
    investigations = db.scalars(
        select(Investigation).order_by(Investigation.updated_at.desc()).limit(5)
    ).all()
    collectors = db.scalars(select(CollectorConfig).order_by(CollectorConfig.name)).all()
    return DashboardResponse(
        entity_total=db.scalar(select(func.count(Entity.id))) or 0,
        investigation_total=db.scalar(select(func.count(Investigation.id))) or 0,
        observation_total=db.scalar(select(func.count(Observation.id))) or 0,
        relationship_total=db.scalar(select(func.count(Relationship.id))) or 0,
        high_risk_total=db.scalar(select(func.count(Entity.id)).where(Entity.risk_score >= 50)) or 0,
        entities_by_type=by_type,
        recent_entities=recent_entities,
        recent_investigations=investigations,
        high_risk_entities=high_risk,
        collectors=collectors,
    )
