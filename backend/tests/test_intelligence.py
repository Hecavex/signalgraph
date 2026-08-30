from __future__ import annotations

from app.intelligence import ObservableError, identify_type, normalize_observable


def create_entity(client, headers, value, **extra):
    response = client.post("/api/v1/entities", headers=headers, json={"value": value, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_identification_and_normalization():
    assert identify_type("203.0.113.42") == "ip_address"
    assert identify_type("HTTPS://Example.COM/login#fragment") == "url"
    assert identify_type("CVE-2025-29927") == "vulnerability"
    assert identify_type("f" * 64) == "file_hash"
    assert normalize_observable("EXAMPLE.COM.") == ("domain", "example.com")
    assert normalize_observable("https://Example.COM/path#secret") == ("url", "https://example.com/path")
    try:
        normalize_observable("file:///etc/passwd", "url")
    except ObservableError:
        pass
    else:
        raise AssertionError("Non-HTTP URL should be rejected")


def test_entities_deduplicate_search_tag_and_explain_risk(client, admin):
    entity = create_entity(
        client,
        admin["headers"],
        "Northstar.EXAMPLE.",
        classification="suspicious",
        confidence=90,
        tags=["Phishing", "northstar"],
    )
    assert entity["normalized_value"] == "northstar.example"
    assert entity["risk_score"] == 40
    assert {item["rule"] for item in entity["risk_explanation"]} == {
        "suspicious_classification",
        "high_confidence",
    }
    duplicate = client.post(
        "/api/v1/entities",
        headers=admin["headers"],
        json={"value": "northstar.example"},
    )
    assert duplicate.status_code == 409
    result = client.get(
        "/api/v1/entities?q=northstar&tag=phishing&page=1&page_size=10",
        headers=admin["headers"],
    )
    assert result.status_code == 200
    assert result.json()["total"] == 1


def test_relationship_graph_depth_and_filters(client, admin):
    domain = create_entity(client, admin["headers"], "graph.example")
    ip = create_entity(client, admin["headers"], "203.0.113.9")
    asn = create_entity(client, admin["headers"], "AS64500")
    for source, target, relation_type in (
        (domain["id"], ip["id"], "resolves_to"),
        (ip["id"], asn["id"], "announced_by"),
    ):
        response = client.post(
            "/api/v1/entities/relationships",
            headers=admin["headers"],
            json={"source_entity_id": source, "target_entity_id": target, "type": relation_type},
        )
        assert response.status_code == 201, response.text
    depth_one = client.get(f"/api/v1/graph/{domain['id']}?depth=1", headers=admin["headers"]).json()
    assert len(depth_one["nodes"]) == 2
    depth_two = client.get(f"/api/v1/graph/{domain['id']}?depth=2", headers=admin["headers"]).json()
    assert len(depth_two["nodes"]) == 3
    filtered = client.get(
        f"/api/v1/graph/{domain['id']}?depth=2&relationship_type=resolves_to",
        headers=admin["headers"],
    ).json()
    assert len(filtered["edges"]) == 1
    entity_filtered = client.get(
        f"/api/v1/graph/{domain['id']}?depth=2&entity_type=ip_address",
        headers=admin["headers"],
    ).json()
    assert {node["type"] for node in entity_filtered["nodes"]} == {"domain", "ip_address"}


def test_enrichment_job_is_queued_without_fetching_target(client, admin, monkeypatch):
    class Queued:
        id = "celery-test-id"

    monkeypatch.setattr("app.api.entities.enrich_task.delay", lambda *args: Queued())
    response = client.post(
        "/api/v1/entities/enrich",
        headers=admin["headers"],
        json={"value": "example.org", "collectors": ["dns"]},
    )
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"
    assert response.json()["task_id"] == "celery-test-id"
