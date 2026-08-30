from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Entity, Relationship


def score_entity(db: Session, entity: Entity) -> tuple[int, list[dict]]:
    rules = get_settings().risk_rules
    score = 0
    explanations: list[dict] = []

    def add(rule: str, reason: str) -> None:
        nonlocal score
        points = int(rules.get(rule, 0))
        if points:
            score += points
            explanations.append({"rule": rule, "points": points, "reason": reason})

    if entity.classification == "malicious":
        add("malicious_classification", "An analyst classified this entity as malicious")
    elif entity.classification == "suspicious":
        add("suspicious_classification", "An analyst classified this entity as suspicious")
    if entity.confidence >= 80 and entity.classification in {"suspicious", "malicious"}:
        add("high_confidence", "The suspicious or malicious assessment has high confidence")
    if entity.type == "vulnerability":
        add("vulnerability_entity", "The observable is a vulnerability requiring prioritization")

    relation_count = (
        db.scalar(
            select(func.count(Relationship.id)).where(
                or_(Relationship.source_entity_id == entity.id, Relationship.target_entity_id == entity.id)
            )
        )
        or 0
    )
    if relation_count >= 5:
        add("many_relationships", f"The entity participates in {relation_count} known relationships")

    return min(score, 100), explanations


def refresh_risk(db: Session, entity: Entity) -> Entity:
    entity.risk_score, entity.risk_explanation = score_entity(db, entity)
    return entity
