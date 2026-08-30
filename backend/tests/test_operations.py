from sqlalchemy import select

from app.database import SessionLocal
from app.models import CollectorConfig, Job
from app.services.enrichment import ensure_collectors


def test_collector_bootstrap_is_idempotent():
    with SessionLocal() as db:
        ensure_collectors(db)
        db.commit()
        ensure_collectors(db)
        db.commit()
        names = db.scalars(select(CollectorConfig.name).order_by(CollectorConfig.name)).all()

    assert names == ["certificate_transparency", "dns", "rdap", "urlscan", "vulnerability"]


def test_failed_job_listing_and_retry_preserve_requested_collectors(client, admin, monkeypatch):
    with SessionLocal() as db:
        original = Job(
            collector="concurrent:dns",
            observable="retry.example",
            created_by=admin["user"]["id"],
            status="failed",
            error="synthetic failure",
            result={"entity_type": "domain", "collectors_requested": ["dns"]},
        )
        db.add(original)
        db.commit()
        original_id = original.id

    class Queued:
        id = "retry-task-id"

    monkeypatch.setattr("app.api.operations.enrich_task.delay", lambda *args: Queued())

    failed = client.get("/api/v1/operations/jobs?failed_only=true", headers=admin["headers"])
    assert failed.status_code == 200
    assert [item["id"] for item in failed.json()] == [original_id]

    retried = client.post(
        f"/api/v1/operations/jobs/{original_id}/retry",
        headers=admin["headers"],
    )
    assert retried.status_code == 202, retried.text
    assert retried.json()["task_id"] == "retry-task-id"
    assert retried.json()["result"]["retry_of"] == original_id
    assert retried.json()["result"]["collectors_requested"] == ["dns"]
