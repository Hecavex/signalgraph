from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.audit import record_audit
from app.database import get_db
from app.deps import require_analyst, require_viewer
from app.intelligence import ObservableError
from app.models import Entity, Job, Note, Relationship, Tag, User
from app.risk import refresh_risk
from app.schemas import (
    EnrichmentRequest,
    EntityCreate,
    EntityDetail,
    EntitySummary,
    EntityUpdate,
    JobOut,
    NoteCreate,
    NoteOut,
    PaginatedEntities,
    RelationshipCreate,
    RelationshipOut,
)
from app.services.enrichment import applicable_collectors
from app.services.entities import get_or_create_entity, set_entity_tags
from app.tasks import enrich_task

router = APIRouter(prefix="/entities", tags=["intelligence"])


def entity_query():
    return select(Entity).options(selectinload(Entity.tags), selectinload(Entity.observations))


def get_entity_or_404(db: Session, entity_id: str) -> Entity:
    entity = db.scalar(entity_query().where(Entity.id == entity_id))
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return entity


@router.get("", response_model=PaginatedEntities)
def list_entities(
    q: str | None = Query(default=None, max_length=256),
    entity_type: str | None = Query(default=None, alias="type", max_length=40),
    classification: str | None = Query(default=None, max_length=24),
    min_risk: int | None = Query(default=None, ge=0, le=100),
    tag: str | None = Query(default=None, max_length=64),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _: User = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> PaginatedEntities:
    conditions = []
    if q:
        like = f"%{q.strip().lower()}%"
        conditions.append(
            or_(func.lower(Entity.value).like(like), func.lower(Entity.display_name).like(like))
        )
    if entity_type:
        conditions.append(Entity.type == entity_type)
    if classification:
        conditions.append(Entity.classification == classification)
    if min_risk is not None:
        conditions.append(Entity.risk_score >= min_risk)

    count_query = select(func.count(Entity.id))
    data_query = select(Entity).options(selectinload(Entity.tags))
    if tag:
        data_query = data_query.join(Entity.tags)
        count_query = count_query.join(Entity.tags)
        conditions.append(Tag.name == tag.lower())
    if conditions:
        data_query = data_query.where(*conditions)
        count_query = count_query.where(*conditions)
    total = db.scalar(count_query) or 0
    items = (
        db.scalars(
            data_query.order_by(Entity.risk_score.desc(), Entity.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )
    return PaginatedEntities(
        items=[EntitySummary.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.post("", response_model=EntityDetail, status_code=status.HTTP_201_CREATED)
def create_entity(
    payload: EntityCreate,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Entity:
    try:
        entity, created = get_or_create_entity(
            db,
            payload.value,
            payload.type,
            actor.id,
            display_name=payload.display_name,
            classification=payload.classification,
            confidence=payload.confidence,
        )
    except ObservableError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if not created:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"message": "Entity already exists", "id": entity.id}
        )
    set_entity_tags(db, entity, payload.tags)
    refresh_risk(db, entity)
    record_audit(db, "entity.create", "entity", entity.id, actor, request, {"type": entity.type})
    db.commit()
    return get_entity_or_404(db, entity.id)


@router.get("/{entity_id}", response_model=EntityDetail)
def get_entity(
    entity_id: str,
    _: User = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> Entity:
    return get_entity_or_404(db, entity_id)


@router.patch("/{entity_id}", response_model=EntityDetail)
def update_entity(
    entity_id: str,
    payload: EntityUpdate,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Entity:
    entity = get_entity_or_404(db, entity_id)
    changes = payload.model_dump(exclude_unset=True)
    tags = changes.pop("tags", None)
    for key, value in changes.items():
        setattr(entity, key, value)
    if tags is not None:
        set_entity_tags(db, entity, tags)
    refresh_risk(db, entity)
    record_audit(db, "entity.update", "entity", entity.id, actor, request, {"fields": sorted(changes)})
    db.commit()
    return get_entity_or_404(db, entity.id)


@router.post("/{entity_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def add_entity_note(
    entity_id: str,
    payload: NoteCreate,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Note:
    get_entity_or_404(db, entity_id)
    note = Note(
        entity_id=entity_id, author_id=actor.id, body=payload.body, classification=payload.classification
    )
    db.add(note)
    db.flush()
    record_audit(db, "entity.note", "entity", entity_id, actor, request)
    db.commit()
    return note


@router.post("/relationships", response_model=RelationshipOut, status_code=status.HTTP_201_CREATED)
def create_relationship(
    payload: RelationshipCreate,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Relationship:
    if payload.source_entity_id == payload.target_entity_id:
        raise HTTPException(status_code=422, detail="Self-relationships are not allowed")
    get_entity_or_404(db, payload.source_entity_id)
    get_entity_or_404(db, payload.target_entity_id)
    existing = db.scalar(
        select(Relationship).where(
            Relationship.source_entity_id == payload.source_entity_id,
            Relationship.target_entity_id == payload.target_entity_id,
            Relationship.type == payload.type,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Relationship already exists")
    relationship = Relationship(**payload.model_dump())
    db.add(relationship)
    db.flush()
    record_audit(db, "relationship.create", "relationship", relationship.id, actor, request)
    db.commit()
    return relationship


@router.post("/enrich", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def enrich_entity(
    payload: EnrichmentRequest,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Job:
    try:
        entity, _ = get_or_create_entity(db, payload.value, payload.type, actor.id)
    except ObservableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    collectors = applicable_collectors(db, entity.type, payload.collectors)
    if not collectors:
        raise HTTPException(status_code=422, detail=f"No enabled collectors support {entity.type}")
    job = Job(
        collector="concurrent:" + ",".join(collectors),
        observable=entity.normalized_value,
        created_by=actor.id,
        result={"entity_id": entity.id, "entity_type": entity.type, "collectors_requested": collectors},
    )
    db.add(job)
    db.flush()
    record_audit(db, "enrichment.queue", "job", job.id, actor, request, {"collectors": collectors})
    db.commit()
    async_result = enrich_task.delay(job.id, collectors)
    job.task_id = async_result.id
    db.commit()
    return job
