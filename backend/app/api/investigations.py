from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit import record_audit
from app.database import get_db
from app.deps import require_analyst, require_viewer
from app.models import (
    Entity,
    Investigation,
    InvestigationEntity,
    InvestigationRelationship,
    Note,
    Relationship,
    User,
)
from app.schemas import (
    GraphEdge,
    GraphNode,
    GraphResponse,
    InvestigationCreate,
    InvestigationDetail,
    InvestigationOut,
    InvestigationUpdate,
    NoteCreate,
    NoteOut,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])


def detail_query():
    return select(Investigation).options(
        selectinload(Investigation.entities).selectinload(InvestigationEntity.entity),
        selectinload(Investigation.relationships),
        selectinload(Investigation.notes).selectinload(Note.author),
    )


def get_investigation(db: Session, investigation_id: str) -> Investigation:
    item = db.scalar(detail_query().where(Investigation.id == investigation_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return item


@router.get("", response_model=list[InvestigationOut])
def list_investigations(
    _: User = Depends(require_viewer), db: Session = Depends(get_db)
) -> list[Investigation]:
    return list(db.scalars(select(Investigation).order_by(Investigation.updated_at.desc())).all())


@router.post("", response_model=InvestigationOut, status_code=status.HTTP_201_CREATED)
def create_investigation(
    payload: InvestigationCreate,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Investigation:
    item = Investigation(**payload.model_dump(), created_by=actor.id)
    db.add(item)
    db.flush()
    record_audit(db, "investigation.create", "investigation", item.id, actor, request)
    db.commit()
    return item


@router.get("/{investigation_id}", response_model=InvestigationDetail)
def investigation_detail(
    investigation_id: str,
    _: User = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> Investigation:
    return get_investigation(db, investigation_id)


@router.patch("/{investigation_id}", response_model=InvestigationOut)
def update_investigation(
    investigation_id: str,
    payload: InvestigationUpdate,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Investigation:
    item = get_investigation(db, investigation_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(item, key, value)
    record_audit(
        db, "investigation.update", "investigation", item.id, actor, request, {"fields": sorted(changes)}
    )
    db.commit()
    return item


@router.post("/{investigation_id}/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_investigation_entity(
    investigation_id: str,
    entity_id: str,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Response:
    get_investigation(db, investigation_id)
    if db.get(Entity, entity_id) is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    existing = db.get(InvestigationEntity, (investigation_id, entity_id))
    if existing is None:
        db.add(InvestigationEntity(investigation_id=investigation_id, entity_id=entity_id, added_by=actor.id))
        db.flush()
    entity_ids = set(
        db.scalars(
            select(InvestigationEntity.entity_id).where(
                InvestigationEntity.investigation_id == investigation_id
            )
        ).all()
    )
    connected = db.scalars(
        select(Relationship).where(
            Relationship.source_entity_id.in_(entity_ids),
            Relationship.target_entity_id.in_(entity_ids),
        )
    ).all()
    for relationship in connected:
        key = (investigation_id, relationship.id)
        if db.get(InvestigationRelationship, key) is None:
            db.add(
                InvestigationRelationship(
                    investigation_id=investigation_id,
                    relationship_id=relationship.id,
                    added_by=actor.id,
                )
            )
    record_audit(
        db,
        "investigation.entity_add",
        "investigation",
        investigation_id,
        actor,
        request,
        {"entity": entity_id},
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{investigation_id}/relationships/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def add_investigation_relationship(
    investigation_id: str,
    relationship_id: str,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Response:
    get_investigation(db, investigation_id)
    relationship = db.get(Relationship, relationship_id)
    if relationship is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    for entity_id in (relationship.source_entity_id, relationship.target_entity_id):
        if db.get(InvestigationEntity, (investigation_id, entity_id)) is None:
            db.add(
                InvestigationEntity(
                    investigation_id=investigation_id,
                    entity_id=entity_id,
                    added_by=actor.id,
                )
            )
    if db.get(InvestigationRelationship, (investigation_id, relationship_id)) is None:
        db.add(
            InvestigationRelationship(
                investigation_id=investigation_id,
                relationship_id=relationship_id,
                added_by=actor.id,
            )
        )
    record_audit(
        db,
        "investigation.relationship_add",
        "investigation",
        investigation_id,
        actor,
        request,
        {"relationship": relationship_id},
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{investigation_id}/graph", response_model=GraphResponse)
def investigation_graph(
    investigation_id: str,
    _: User = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> GraphResponse:
    item = get_investigation(db, investigation_id)
    entities = [linked.entity for linked in item.entities]
    relationships = [linked.relationship for linked in item.relationships]
    return GraphResponse(
        nodes=[
            GraphNode(
                id=entity.id,
                label=entity.display_name or entity.value,
                type=entity.type,
                risk_score=entity.risk_score,
                classification=entity.classification,
            )
            for entity in entities
        ],
        edges=[
            GraphEdge(
                id=relationship.id,
                source=relationship.source_entity_id,
                target=relationship.target_entity_id,
                type=relationship.type,
                confidence=relationship.confidence,
            )
            for relationship in relationships
        ],
        depth=1,
    )


@router.post("/{investigation_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def add_investigation_note(
    investigation_id: str,
    payload: NoteCreate,
    request: Request,
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> Note:
    get_investigation(db, investigation_id)
    note = Note(
        investigation_id=investigation_id,
        author_id=actor.id,
        body=payload.body,
        classification=payload.classification,
    )
    db.add(note)
    db.flush()
    record_audit(db, "investigation.note", "investigation", investigation_id, actor, request)
    db.commit()
    return note


@router.get("/{investigation_id}/timeline")
def investigation_timeline(
    investigation_id: str,
    _: User = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> list[dict]:
    item = get_investigation(db, investigation_id)
    events = [
        {"type": "created", "at": item.created_at, "label": f"Investigation created: {item.title}"},
        *[
            {"type": "entity_added", "at": linked.added_at, "label": f"Added {linked.entity.value}"}
            for linked in item.entities
        ],
        *[
            {
                "type": "relationship_added",
                "at": linked.added_at,
                "label": f"Added relationship {linked.relationship.type.replace('_', ' ')}",
            }
            for linked in item.relationships
        ],
        *[
            {"type": "note", "at": note.created_at, "label": note.body, "author": note.author.display_name}
            for note in item.notes
        ],
    ]
    return sorted(events, key=lambda event: event["at"], reverse=True)


@router.get("/{investigation_id}/export")
def export_investigation(
    investigation_id: str,
    _: User = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> Response:
    item = get_investigation(db, investigation_id)
    payload = {
        "signalgraph_version": "1.0.0",
        "investigation": {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "status": item.status,
            "assessment": item.assessment,
            "confidence": item.confidence,
            "entities": [
                {"id": linked.entity.id, "type": linked.entity.type, "value": linked.entity.value}
                for linked in item.entities
            ],
            "relationships": [linked.relationship_id for linked in item.relationships],
            "notes": [{"body": note.body, "created_at": note.created_at.isoformat()} for note in item.notes],
        },
    }
    return Response(
        json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="investigation-{item.id}.json"'},
    )
