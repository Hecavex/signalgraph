from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False
    )


entity_tags = Table(
    "entity_tags",
    Base.metadata,
    Column("entity_id", String(36), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


report_entities = Table(
    "report_entities",
    Base.metadata,
    Column("report_id", String(36), ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True),
    Column("entity_id", String(36), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True),
)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (CheckConstraint("role IN ('admin','analyst','viewer')", name="ck_user_role"),)


class Tag(TimestampMixin, Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#73d7c7")


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="collector")
    url: Mapped[str | None] = mapped_column(String(2048))
    reliability: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    description: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (CheckConstraint("reliability BETWEEN 0 AND 100", name="ck_source_reliability"),)


class Entity(TimestampMixin, Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    value: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(2048), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_explanation: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))

    tags: Mapped[list[Tag]] = relationship(secondary=entity_tags, lazy="selectin")
    observations: Mapped[list[Observation]] = relationship(
        back_populates="entity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("type", "normalized_value", name="uq_entity_type_value"),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_entity_confidence"),
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_entity_risk"),
        CheckConstraint(
            "classification IN ('unknown','benign','suspicious','malicious')",
            name="ck_entity_classification",
        ),
        Index("ix_entity_search", "normalized_value", "display_name"),
    )


class RawResponse(Base):
    __tablename__ = "raw_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    collector: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    observable: Mapped[str] = mapped_column(String(2048), nullable=False)
    request_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict | list] = mapped_column(JSON, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("sources.id", ondelete="RESTRICT"))
    raw_response_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("raw_responses.id", ondelete="SET NULL")
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    entity: Mapped[Entity] = relationship(back_populates="observations")
    source: Mapped[Source] = relationship(lazy="joined")
    raw_response: Mapped[RawResponse | None] = relationship(lazy="joined")

    __table_args__ = (CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_observation_confidence"),)


class Relationship(TimestampMixin, Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    target_entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    source_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sources.id", ondelete="SET NULL"))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    source_entity: Mapped[Entity] = relationship(foreign_keys=[source_entity_id], lazy="joined")
    target_entity: Mapped[Entity] = relationship(foreign_keys=[target_entity_id], lazy="joined")
    provenance_source: Mapped[Source | None] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("source_entity_id", "target_entity_id", "type", name="uq_relationship_edge"),
        CheckConstraint("source_entity_id <> target_entity_id", name="ck_relationship_not_self"),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_relationship_confidence"),
    )


class Investigation(TimestampMixin, Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    assessment: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))

    entities: Mapped[list[InvestigationEntity]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan", lazy="selectin"
    )
    relationships: Mapped[list[InvestigationRelationship]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan", lazy="selectin"
    )
    notes: Mapped[list[Note]] = relationship(back_populates="investigation", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('open','investigating','monitoring','closed')", name="ck_investigation_status"
        ),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_investigation_confidence"),
    )


class InvestigationEntity(Base):
    __tablename__ = "investigation_entities"

    investigation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("investigations.id", ondelete="CASCADE"), primary_key=True
    )
    entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    added_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    investigation: Mapped[Investigation] = relationship(back_populates="entities")
    entity: Mapped[Entity] = relationship(lazy="joined")


class InvestigationRelationship(Base):
    __tablename__ = "investigation_relationships"

    investigation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("investigations.id", ondelete="CASCADE"), primary_key=True
    )
    relationship_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("relationships.id", ondelete="CASCADE"), primary_key=True
    )
    added_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    investigation: Mapped[Investigation] = relationship(back_populates="relationships")
    relationship: Mapped[Relationship] = relationship(lazy="joined")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id", ondelete="CASCADE"))
    investigation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("investigations.id", ondelete="CASCADE")
    )
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(String(24), nullable=False, default="internal")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    investigation: Mapped[Investigation | None] = relationship(back_populates="notes")
    author: Mapped[User] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint("entity_id IS NOT NULL OR investigation_id IS NOT NULL", name="ck_note_parent"),
    )


class CollectorConfig(TimestampMixin, Base):
    __tablename__ = "collector_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str | None] = mapped_column(String(80), index=True)
    collector: Mapped[str] = mapped_column(String(80), nullable=False)
    observable: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assessment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    entities: Mapped[list[Entity]] = relationship(secondary=report_entities, lazy="selectin")

    __table_args__ = (CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_report_confidence"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(80))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
