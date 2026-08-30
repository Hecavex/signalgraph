from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.collectors import COLLECTORS, get_collector
from app.collectors.base import CollectorResult
from app.config import get_settings
from app.models import CollectorConfig, Job, Observation, RawResponse, Relationship, Source
from app.risk import refresh_risk
from app.services.entities import get_or_create_entity


def ensure_collectors(db: Session) -> None:
    defaults = {
        "dns": (True, 120),
        "rdap": (True, 30),
        "certificate_transparency": (True, 20),
        "vulnerability": (True, 30),
        "urlscan": (False, 20),
    }
    for name, (enabled, rate) in defaults.items():
        if db.scalar(select(CollectorConfig).where(CollectorConfig.name == name)) is None:
            try:
                with db.begin_nested():
                    db.add(CollectorConfig(name=name, enabled=enabled, rate_limit_per_minute=rate))
                    db.flush()
            except IntegrityError:
                # Another API worker may have inserted the same default after our SELECT.
                # The savepoint keeps the outer startup transaction usable.
                continue


def applicable_collectors(db: Session, entity_type: str, requested: list[str] | None = None) -> list[str]:
    ensure_collectors(db)
    configs = {item.name: item for item in db.scalars(select(CollectorConfig)).all()}
    names = requested or list(COLLECTORS)
    return [
        name
        for name in names
        if name in COLLECTORS
        and configs.get(name)
        and configs[name].enabled
        and COLLECTORS[name].supports(entity_type)
    ]


def _collect(name: str, value: str, entity_type: str, config: CollectorConfig) -> CollectorResult:
    collector = get_collector(name)
    collector.throttle(config.rate_limit_per_minute)
    return collector.collect(value, entity_type, config.timeout_seconds)


def _store_result(db: Session, entity, result: CollectorResult) -> dict:
    settings = get_settings()
    encoded = json.dumps(result.payload, default=str).encode()
    payload = result.payload
    if len(encoded) > settings.raw_response_max_bytes:
        payload = {
            "truncated": True,
            "original_bytes": len(encoded),
            "preview": encoded[:65536].decode(errors="replace"),
        }
    raw = RawResponse(
        collector=result.collector,
        observable=entity.normalized_value,
        request_url=result.request_url,
        status_code=result.status_code,
        payload=payload,
        sha256=result.sha256,
    )
    db.add(raw)
    db.flush()
    source = db.scalar(select(Source).where(Source.name == result.collector))
    if source is None:
        source = Source(
            name=result.collector, kind="collector", url=get_collector(result.collector).source_url
        )
        db.add(source)
        db.flush()
    db.add(
        Observation(
            entity_id=entity.id,
            source_id=source.id,
            raw_response_id=raw.id,
            confidence=70,
            data=result.observations,
        )
    )
    relation_ids: list[str] = []
    for item in result.relations:
        try:
            related, _ = get_or_create_entity(db, item.value, item.entity_type)
        except ValueError:
            continue
        if related.id == entity.id:
            continue
        relationship = db.scalar(
            select(Relationship).where(
                Relationship.source_entity_id == entity.id,
                Relationship.target_entity_id == related.id,
                Relationship.type == item.relation_type,
            )
        )
        if relationship is None:
            relationship = Relationship(
                source_entity_id=entity.id,
                target_entity_id=related.id,
                type=item.relation_type,
                confidence=item.confidence,
                source_id=source.id,
                attributes=item.attributes,
            )
            db.add(relationship)
            db.flush()
        else:
            relationship.last_seen = datetime.now(UTC)
        relation_ids.append(relationship.id)
        refresh_risk(db, related)
    refresh_risk(db, entity)
    return {"observation": result.observations, "relationships": relation_ids, "raw_response": raw.id}


def run_job(db: Session, job_id: str, collector_names: list[str]) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise ValueError("Job not found")
    entity, _ = get_or_create_entity(db, job.observable, job.result.get("entity_type"))
    ensure_collectors(db)
    configs = {item.name: item for item in db.scalars(select(CollectorConfig)).all()}
    job.status = "running"
    job.started_at = datetime.now(UTC)
    job.attempts += 1
    db.commit()

    outputs: dict[str, dict] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(collector_names)))) as executor:
        futures = {
            executor.submit(_collect, name, entity.normalized_value, entity.type, configs[name]): name
            for name in collector_names
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                outputs[name] = _store_result(db, entity, future.result())
                configs[name].last_success_at = datetime.now(UTC)
                configs[name].last_error = None
            except Exception as exc:  # collector errors are persisted for analyst inspection
                errors[name] = f"{type(exc).__name__}: {exc}"[:2000]
                configs[name].last_error_at = datetime.now(UTC)
                configs[name].last_error = errors[name]

    job.result = {
        "entity_id": entity.id,
        "entity_type": entity.type,
        "collectors_requested": collector_names,
        "collectors": outputs,
        "errors": errors,
    }
    job.error = "; ".join(f"{name}: {error}" for name, error in errors.items()) or None
    job.status = "completed" if outputs and not errors else "partial" if outputs else "failed"
    job.finished_at = datetime.now(UTC)
    db.commit()
    return job.result
