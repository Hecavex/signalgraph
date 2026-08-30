from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.intelligence import normalize_observable
from app.models import Entity, Tag
from app.risk import refresh_risk


def get_or_create_entity(
    db: Session,
    value: str,
    entity_type: str | None = None,
    created_by: str | None = None,
    **attributes,
) -> tuple[Entity, bool]:
    detected, normalized = normalize_observable(value, entity_type)
    entity = db.scalar(select(Entity).where(Entity.type == detected, Entity.normalized_value == normalized))
    if entity:
        entity.last_seen = datetime.now(UTC)
        return entity, False
    entity = Entity(
        type=detected,
        value=value.strip(),
        normalized_value=normalized,
        created_by=created_by,
        **attributes,
    )
    db.add(entity)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        entity = db.scalar(
            select(Entity).where(Entity.type == detected, Entity.normalized_value == normalized)
        )
        if entity is None:
            raise
        return entity, False
    refresh_risk(db, entity)
    return entity, True


def set_entity_tags(db: Session, entity: Entity, names: list[str]) -> None:
    clean_names = sorted({name.strip().lower() for name in names if name.strip()})
    tags: list[Tag] = []
    for name in clean_names:
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    entity.tags = tags
