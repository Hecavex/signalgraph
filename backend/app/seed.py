from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Investigation,
    InvestigationEntity,
    InvestigationRelationship,
    Note,
    Observation,
    Relationship,
    Report,
    Source,
    User,
)
from app.risk import refresh_risk
from app.security import hash_password
from app.services.enrichment import ensure_collectors
from app.services.entities import get_or_create_entity, set_entity_tags

DEMO_ENTITIES = [
    ("domain", "northstar-login.example", "suspicious", 88, ["phishing", "northstar"]),
    ("ip_address", "203.0.113.42", "suspicious", 74, ["shared-hosting"]),
    ("domain", "northstar-auth.example", "suspicious", 82, ["phishing", "northstar"]),
    ("certificate", "03A7F92E91B4", "unknown", 65, ["certificate"]),
    ("asn", "AS64500", "unknown", 70, ["infrastructure"]),
    ("organization", "Example Transit Labs", "unknown", 55, ["hosting"]),
    ("vulnerability", "CVE-2025-29927", "suspicious", 90, ["vulnerability", "watch"]),
    ("file_hash", "f" * 64, "malicious", 96, ["malware", "ioc"]),
    ("malware", "Paper Lantern Loader", "malicious", 86, ["malware"]),
]


def seed_demo(db: Session, admin_email: str, password: str) -> dict:
    admin = db.scalar(select(User).where(User.email == admin_email))
    if admin is None:
        admin = User(
            email=admin_email,
            display_name="Demo Analyst",
            password_hash=hash_password(password),
            role="admin",
        )
        db.add(admin)
        db.flush()

    entities = {}
    for entity_type, value, classification, confidence, tags in DEMO_ENTITIES:
        entity, _ = get_or_create_entity(
            db,
            value,
            entity_type,
            admin.id,
            classification=classification,
            confidence=confidence,
        )
        if entity_type == "file_hash":
            entity.display_name = "Paper Lantern SHA-256"
        set_entity_tags(db, entity, tags)
        refresh_risk(db, entity)
        entities[value] = entity

    source = db.scalar(select(Source).where(Source.name == "demo-dataset"))
    if source is None:
        source = Source(
            name="demo-dataset",
            kind="synthetic",
            reliability=80,
            description="Clearly labeled synthetic data shipped for evaluation and screenshots.",
        )
        db.add(source)
        db.flush()

    domain = entities["northstar-login.example"]
    if not domain.observations:
        db.add(
            Observation(
                entity_id=domain.id,
                source_id=source.id,
                confidence=88,
                observed_at=datetime.now(UTC) - timedelta(hours=3),
                data={
                    "record": "A",
                    "answer": "203.0.113.42",
                    "note": "Synthetic passive DNS observation",
                },
            )
        )

    edges = [
        ("northstar-login.example", "203.0.113.42", "resolves_to", 90),
        ("northstar-auth.example", "203.0.113.42", "resolves_to", 88),
        ("northstar-login.example", "03A7F92E91B4", "observed_in_certificate", 84),
        ("northstar-auth.example", "03A7F92E91B4", "shares_certificate", 79),
        ("203.0.113.42", "AS64500", "announced_by", 92),
        ("AS64500", "Example Transit Labs", "operated_by", 78),
        ("f" * 64, "Paper Lantern Loader", "sample_of", 96),
    ]
    for source_value, target_value, relation_type, confidence in edges:
        source_entity = entities[source_value]
        target_entity = entities[target_value]
        existing = db.scalar(
            select(Relationship).where(
                Relationship.source_entity_id == source_entity.id,
                Relationship.target_entity_id == target_entity.id,
                Relationship.type == relation_type,
            )
        )
        if existing is None:
            db.add(
                Relationship(
                    source_entity_id=source_entity.id,
                    target_entity_id=target_entity.id,
                    type=relation_type,
                    confidence=confidence,
                    source_id=source.id,
                    attributes={"dataset": "synthetic"},
                )
            )
    db.flush()
    for entity in entities.values():
        refresh_risk(db, entity)

    investigation = db.scalar(select(Investigation).where(Investigation.title == "Northstar credential lure"))
    if investigation is None:
        investigation = Investigation(
            title="Northstar credential lure",
            description="Assess a synthetic cluster of lookalike authentication infrastructure.",
            status="investigating",
            priority="high",
            assessment=(
                "Shared infrastructure and certificate reuse support a single operational cluster. "
                "Attribution is not assessed."
            ),
            confidence=82,
            created_by=admin.id,
        )
        db.add(investigation)
        db.flush()
        for value in ("northstar-login.example", "northstar-auth.example", "203.0.113.42", "03A7F92E91B4"):
            db.add(
                InvestigationEntity(
                    investigation_id=investigation.id, entity_id=entities[value].id, added_by=admin.id
                )
            )
        db.add(
            Note(
                investigation_id=investigation.id,
                author_id=admin.id,
                body="Certificate reuse links both domains; confirm with passive sources before escalation.",
            )
        )

    db.flush()
    case_entity_ids = set(
        db.scalars(
            select(InvestigationEntity.entity_id).where(
                InvestigationEntity.investigation_id == investigation.id
            )
        ).all()
    )
    case_relationships = db.scalars(
        select(Relationship).where(
            Relationship.source_entity_id.in_(case_entity_ids),
            Relationship.target_entity_id.in_(case_entity_ids),
        )
    ).all()
    for relationship in case_relationships:
        if db.get(InvestigationRelationship, (investigation.id, relationship.id)) is None:
            db.add(
                InvestigationRelationship(
                    investigation_id=investigation.id,
                    relationship_id=relationship.id,
                    added_by=admin.id,
                )
            )

    report = db.scalar(select(Report).where(Report.title == "Northstar infrastructure assessment"))
    if report is None:
        report = Report(
            title="Northstar infrastructure assessment",
            executive_summary="Synthetic authentication lures share hosting and certificate material.",
            assessment=(
                "The observed overlap is consistent with coordinated infrastructure. "
                "It does not establish actor attribution."
            ),
            confidence=82,
            created_by=admin.id,
            entities=[domain, entities["northstar-auth.example"], entities["203.0.113.42"]],
        )
        db.add(report)

    ensure_collectors(db)
    db.commit()
    return {
        "admin_email": admin.email,
        "entities": len(entities),
        "investigation": investigation.id,
        "report": report.id,
    }
