from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Role = Literal["admin", "analyst", "viewer"]
Classification = Literal["unknown", "benign", "suspicious", "malicious"]
InvestigationStatus = Literal["open", "investigating", "monitoring", "closed"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=256)
    role: Role = "viewer"

    @field_validator("password")
    @classmethod
    def password_complexity(cls, value: str) -> str:
        classes = [
            any(c.islower() for c in value),
            any(c.isupper() for c in value),
            any(c.isdigit() for c in value),
        ]
        if sum(classes) < 2:
            raise ValueError("password must contain at least two of: lowercase, uppercase, digits")
        return value


class UserOut(ORMModel):
    id: str
    email: EmailStr
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class AuthStatus(BaseModel):
    bootstrap_required: bool


class TagOut(ORMModel):
    id: str
    name: str
    color: str


class SourceOut(ORMModel):
    id: str
    name: str
    kind: str
    url: str | None
    reliability: int


class RawResponseOut(ORMModel):
    id: str
    collector: str
    request_url: str
    status_code: int
    sha256: str
    payload: dict | list
    collected_at: datetime


class ObservationOut(ORMModel):
    id: str
    observed_at: datetime
    confidence: int
    data: dict
    source: SourceOut
    raw_response: RawResponseOut | None = None


class EntityCreate(BaseModel):
    value: str = Field(min_length=1, max_length=2048)
    type: str | None = Field(default=None, max_length=40)
    display_name: str | None = Field(default=None, max_length=512)
    classification: Classification = "unknown"
    confidence: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list, max_length=20)


class EntityUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=10_000)
    classification: Classification | None = None
    confidence: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] | None = Field(default=None, max_length=20)


class EntitySummary(ORMModel):
    id: str
    type: str
    value: str
    normalized_value: str
    display_name: str | None
    classification: Classification
    confidence: int
    risk_score: int
    risk_explanation: list
    first_seen: datetime
    last_seen: datetime
    tags: list[TagOut]


class EntityDetail(EntitySummary):
    description: str | None
    observations: list[ObservationOut]


class PaginatedEntities(BaseModel):
    items: list[EntitySummary]
    total: int
    page: int
    page_size: int
    pages: int


class EnrichmentRequest(BaseModel):
    value: str = Field(min_length=1, max_length=2048)
    type: str | None = Field(default=None, max_length=40)
    collectors: list[str] | None = None


class RelationshipCreate(BaseModel):
    source_entity_id: str
    target_entity_id: str
    type: str = Field(min_length=2, max_length=80)
    confidence: int = Field(default=50, ge=0, le=100)
    attributes: dict[str, Any] = Field(default_factory=dict)


class RelationshipOut(ORMModel):
    id: str
    source_entity_id: str
    target_entity_id: str
    type: str
    confidence: int
    first_seen: datetime
    last_seen: datetime
    attributes: dict


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=20_000)
    classification: str = Field(default="internal", max_length=24)


class NoteOut(ORMModel):
    id: str
    body: str
    classification: str
    created_at: datetime
    author: UserOut


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str | None = Field(default=None, max_length=20_000)
    priority: Literal["low", "medium", "high", "critical"] = "medium"


class InvestigationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    description: str | None = Field(default=None, max_length=20_000)
    status: InvestigationStatus | None = None
    priority: Literal["low", "medium", "high", "critical"] | None = None
    assessment: str | None = Field(default=None, max_length=50_000)
    confidence: int | None = Field(default=None, ge=0, le=100)


class InvestigationEntityOut(ORMModel):
    entity: EntitySummary
    added_at: datetime


class InvestigationRelationshipOut(ORMModel):
    relationship: RelationshipOut
    added_at: datetime


class InvestigationOut(ORMModel):
    id: str
    title: str
    description: str | None
    status: InvestigationStatus
    priority: str
    assessment: str | None
    confidence: int
    created_at: datetime
    updated_at: datetime


class InvestigationDetail(InvestigationOut):
    entities: list[InvestigationEntityOut]
    relationships: list[InvestigationRelationshipOut]
    notes: list[NoteOut]


class ReportCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    executive_summary: str = Field(default="", max_length=50_000)
    assessment: str = Field(default="", max_length=100_000)
    confidence: int = Field(default=0, ge=0, le=100)
    entity_ids: list[str] = Field(default_factory=list, max_length=500)


class ReportOut(ORMModel):
    id: str
    title: str
    executive_summary: str
    assessment: str
    confidence: int
    status: str
    created_at: datetime
    updated_at: datetime
    entities: list[EntitySummary]


class CollectorConfigOut(ORMModel):
    id: str
    name: str
    enabled: bool
    rate_limit_per_minute: int
    timeout_seconds: int
    max_retries: int
    configuration: dict
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error: str | None


class CollectorConfigUpdate(BaseModel):
    enabled: bool | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=600)
    timeout_seconds: int | None = Field(default=None, ge=1, le=120)
    max_retries: int | None = Field(default=None, ge=0, le=10)
    configuration: dict | None = None


class JobOut(ORMModel):
    id: str
    task_id: str | None
    collector: str
    observable: str
    status: str
    attempts: int
    error: str | None
    result: dict
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    risk_score: int
    classification: str


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    confidence: int


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    depth: int


class DashboardResponse(BaseModel):
    entity_total: int
    investigation_total: int
    observation_total: int
    relationship_total: int
    high_risk_total: int
    entities_by_type: dict[str, int]
    recent_entities: list[EntitySummary]
    recent_investigations: list[InvestigationOut]
    high_risk_entities: list[EntitySummary]
    collectors: list[CollectorConfigOut]
