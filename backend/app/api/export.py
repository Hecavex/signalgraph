from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.database import get_db
from app.deps import require_analyst, require_viewer
from app.models import Entity, Relationship, User
from app.services.entities import get_or_create_entity

router = APIRouter(prefix="/exchange", tags=["import-export"])
STIX_NAMESPACE = uuid.UUID("7b27ef38-2672-4f84-a3e9-b7dc25ee47d6")
TYPE_TO_STIX = {
    "domain": "domain-name",
    "hostname": "domain-name",
    "ip_address": "ip-addr",
    "url": "url",
    "email_address": "email-addr",
    "file_hash": "file",
    "certificate": "x509-certificate",
    "asn": "autonomous-system",
    "organization": "identity",
    "malware": "malware",
    "threat_actor": "threat-actor",
    "campaign": "campaign",
    "infrastructure": "infrastructure",
    "vulnerability": "vulnerability",
    "attack_pattern": "attack-pattern",
    "report": "report",
}


def stix_id(stix_type: str, internal_id: str) -> str:
    if stix_type == "ip-addr":
        stix_type = "ipv6-addr" if ":" in internal_id else "ipv4-addr"
    return f"{stix_type}--{uuid.uuid5(STIX_NAMESPACE, internal_id)}"


def entity_to_stix(entity: Entity) -> dict:
    stix_type = TYPE_TO_STIX.get(entity.type, "identity")
    if stix_type == "ip-addr":
        stix_type = "ipv6-addr" if ":" in entity.normalized_value else "ipv4-addr"
    created = entity.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    modified = entity.updated_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    obj: dict = {"type": stix_type, "spec_version": "2.1", "id": stix_id(stix_type, entity.id)}
    if stix_type in {"domain-name", "ipv4-addr", "ipv6-addr", "url", "email-addr"}:
        obj["value"] = entity.normalized_value
    elif stix_type == "file":
        algorithm = {32: "MD5", 40: "SHA-1", 64: "SHA-256"}[len(entity.normalized_value)]
        obj["hashes"] = {algorithm: entity.normalized_value}
    elif stix_type == "x509-certificate":
        obj["serial_number"] = entity.normalized_value
    elif stix_type == "autonomous-system":
        obj["number"] = int(entity.normalized_value.removeprefix("AS"))
    else:
        obj.update({"created": created, "modified": modified, "name": entity.display_name or entity.value})
        if stix_type == "identity":
            obj["identity_class"] = "organization" if entity.type == "organization" else "system"
        if stix_type == "malware":
            obj.update({"is_family": True, "malware_types": ["unknown"]})
        if stix_type == "threat-actor":
            obj["threat_actor_types"] = ["unknown"]
        if stix_type == "infrastructure":
            obj["infrastructure_types"] = ["unknown"]
    obj["x_signalgraph"] = {
        "classification": entity.classification,
        "confidence": entity.confidence,
        "risk_score": entity.risk_score,
        "risk_explanation": entity.risk_explanation,
    }
    return obj


@router.get("/json")
def export_json(_: User = Depends(require_viewer), db: Session = Depends(get_db)) -> Response:
    entities = db.scalars(select(Entity)).all()
    relationships = db.scalars(select(Relationship)).all()
    payload = {
        "format": "signalgraph-json",
        "version": "1.0",
        "exported_at": datetime.now(UTC).isoformat(),
        "entities": [
            {
                "id": item.id,
                "type": item.type,
                "value": item.value,
                "classification": item.classification,
                "confidence": item.confidence,
                "risk_score": item.risk_score,
                "risk_explanation": item.risk_explanation,
            }
            for item in entities
        ],
        "relationships": [
            {
                "source": item.source_entity_id,
                "target": item.target_entity_id,
                "type": item.type,
                "confidence": item.confidence,
            }
            for item in relationships
        ],
    }
    return Response(
        json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="signalgraph-intelligence.json"'},
    )


@router.get("/csv")
def export_csv(_: User = Depends(require_viewer), db: Session = Depends(get_db)) -> Response:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        ["type", "value", "classification", "confidence", "risk_score", "first_seen", "last_seen"]
    )
    for entity in db.scalars(select(Entity).order_by(Entity.type, Entity.normalized_value)).all():
        writer.writerow(
            [
                entity.type,
                entity.normalized_value,
                entity.classification,
                entity.confidence,
                entity.risk_score,
                entity.first_seen.isoformat(),
                entity.last_seen.isoformat(),
            ]
        )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="signalgraph-iocs.csv"'},
    )


@router.get("/stix")
def export_stix(_: User = Depends(require_viewer), db: Session = Depends(get_db)) -> Response:
    entities = db.scalars(select(Entity)).all()
    entity_map = {item.id: entity_to_stix(item) for item in entities}
    objects = list(entity_map.values())
    for edge in db.scalars(select(Relationship)).all():
        source = entity_map.get(edge.source_entity_id)
        target = entity_map.get(edge.target_entity_id)
        if not source or not target:
            continue
        objects.append(
            {
                "type": "relationship",
                "spec_version": "2.1",
                "id": f"relationship--{uuid.uuid5(STIX_NAMESPACE, edge.id)}",
                "created": edge.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "modified": edge.updated_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "relationship_type": edge.type.replace("_", "-"),
                "source_ref": source["id"],
                "target_ref": target["id"],
                "confidence": edge.confidence,
            }
        )
    bundle = {"type": "bundle", "id": f"bundle--{uuid.uuid4()}", "objects": objects}
    return Response(
        json.dumps(bundle, indent=2),
        media_type="application/stix+json;version=2.1",
        headers={"Content-Disposition": 'attachment; filename="signalgraph-stix-2.1.json"'},
    )


@router.post("/stix/import", status_code=status.HTTP_201_CREATED)
async def import_stix(
    request: Request,
    file: UploadFile = File(...),
    actor: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> dict:
    if file.content_type not in {"application/json", "application/stix+json", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Expected a JSON or STIX JSON file")
    content = await file.read(5_000_001)
    if len(content) > 5_000_000:
        raise HTTPException(status_code=413, detail="STIX bundle exceeds 5 MB")
    try:
        bundle = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Invalid JSON") from exc
    if (
        not isinstance(bundle, dict)
        or bundle.get("type") != "bundle"
        or not isinstance(bundle.get("objects"), list)
    ):
        raise HTTPException(status_code=422, detail="Expected a STIX 2.1 bundle")
    stix_to_internal = {
        "domain-name": "domain",
        "ipv4-addr": "ip_address",
        "ipv6-addr": "ip_address",
        "url": "url",
        "email-addr": "email_address",
        "file": "file_hash",
        "x509-certificate": "certificate",
        "autonomous-system": "asn",
        "identity": "organization",
        "malware": "malware",
        "threat-actor": "threat_actor",
        "campaign": "campaign",
        "infrastructure": "infrastructure",
        "vulnerability": "vulnerability",
        "attack-pattern": "attack_pattern",
        "report": "report",
    }
    imported = 0
    skipped = 0
    for obj in bundle["objects"][:10_000]:
        if not isinstance(obj, dict) or obj.get("type") not in stix_to_internal:
            skipped += 1
            continue
        obj_type = obj["type"]
        value = obj.get("value") or obj.get("name") or obj.get("serial_number")
        if obj_type == "autonomous-system" and obj.get("number") is not None:
            value = f"AS{obj['number']}"
        if obj_type == "file" and obj.get("hashes"):
            value = next(iter(obj["hashes"].values()), None)
        if not value:
            skipped += 1
            continue
        try:
            get_or_create_entity(db, str(value), stix_to_internal[obj_type], actor.id)
            imported += 1
        except ValueError:
            skipped += 1
    record_audit(
        db,
        "stix.import",
        "bundle",
        actor=actor,
        request=request,
        details={"imported": imported, "skipped": skipped},
    )
    db.commit()
    return {"imported": imported, "skipped": skipped}
