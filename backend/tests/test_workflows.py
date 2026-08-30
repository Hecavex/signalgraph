from __future__ import annotations

import json


def entity(client, headers, value):
    response = client.post("/api/v1/entities", headers=headers, json={"value": value})
    assert response.status_code == 201, response.text
    return response.json()


def test_investigation_notes_timeline_and_export(client, admin):
    observable = entity(client, admin["headers"], "case.example")
    created = client.post(
        "/api/v1/investigations",
        headers=admin["headers"],
        json={
            "title": "Case example",
            "description": "Investigate synthetic infrastructure",
            "priority": "high",
        },
    )
    assert created.status_code == 201, created.text
    investigation = created.json()
    add = client.post(
        f"/api/v1/investigations/{investigation['id']}/entities/{observable['id']}",
        headers=admin["headers"],
    )
    assert add.status_code == 204
    note = client.post(
        f"/api/v1/investigations/{investigation['id']}/notes",
        headers=admin["headers"],
        json={"body": "Evidence reviewed; attribution remains open."},
    )
    assert note.status_code == 201, note.text
    update = client.patch(
        f"/api/v1/investigations/{investigation['id']}",
        headers=admin["headers"],
        json={"status": "investigating", "assessment": "One infrastructure overlap", "confidence": 65},
    )
    assert update.status_code == 200
    detail = client.get(
        f"/api/v1/investigations/{investigation['id']}", headers=admin["headers"]
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["entities"][0]["entity"]["value"] == "case.example"
    timeline = client.get(
        f"/api/v1/investigations/{investigation['id']}/timeline", headers=admin["headers"]
    )
    assert len(timeline.json()) == 3
    exported = client.get(
        f"/api/v1/investigations/{investigation['id']}/export", headers=admin["headers"]
    )
    assert exported.status_code == 200
    assert json.loads(exported.text)["investigation"]["status"] == "investigating"


def test_json_csv_stix_report_and_stix_import(client, admin):
    observable = entity(client, admin["headers"], "intel.example")
    report = client.post(
        "/api/v1/reports",
        headers=admin["headers"],
        json={
            "title": "Infrastructure note",
            "executive_summary": "Synthetic indicator reviewed.",
            "assessment": "No attribution is made.",
            "confidence": 70,
            "entity_ids": [observable["id"]],
        },
    )
    assert report.status_code == 201, report.text
    markdown = client.get(
        f"/api/v1/reports/{report.json()['id']}/markdown", headers=admin["headers"]
    )
    assert "# Infrastructure note" in markdown.text
    assert "intel.example" in markdown.text

    assert client.get("/api/v1/exchange/json", headers=admin["headers"]).status_code == 200
    csv_response = client.get("/api/v1/exchange/csv", headers=admin["headers"])
    assert "type,value,classification" in csv_response.text
    stix = client.get("/api/v1/exchange/stix", headers=admin["headers"])
    assert stix.status_code == 200
    bundle = stix.json()
    assert bundle["type"] == "bundle"
    assert any(item["type"] == "domain-name" for item in bundle["objects"])

    incoming = {
        "type": "bundle",
        "id": "bundle--00000000-0000-4000-8000-000000000001",
        "objects": [
            {
                "type": "domain-name",
                "spec_version": "2.1",
                "id": "domain-name--00000000-0000-4000-8000-000000000002",
                "value": "imported.example",
            }
        ],
    }
    imported = client.post(
        "/api/v1/exchange/stix/import",
        headers=admin["headers"],
        files={"file": ("bundle.json", json.dumps(incoming), "application/stix+json")},
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["imported"] == 1


def test_investigation_captures_relationships_and_serves_case_graph(client, admin):
    domain = entity(client, admin["headers"], "linked-case.example")
    ip = entity(client, admin["headers"], "203.0.113.77")
    relationship = client.post(
        "/api/v1/entities/relationships",
        headers=admin["headers"],
        json={
            "source_entity_id": domain["id"],
            "target_entity_id": ip["id"],
            "type": "resolves_to",
            "confidence": 80,
        },
    )
    assert relationship.status_code == 201, relationship.text
    investigation = client.post(
        "/api/v1/investigations",
        headers=admin["headers"],
        json={"title": "Connected case", "priority": "medium"},
    ).json()
    for observable in (domain, ip):
        response = client.post(
            f"/api/v1/investigations/{investigation['id']}/entities/{observable['id']}",
            headers=admin["headers"],
        )
        assert response.status_code == 204
    detail = client.get(
        f"/api/v1/investigations/{investigation['id']}", headers=admin["headers"]
    ).json()
    assert detail["relationships"][0]["relationship"]["type"] == "resolves_to"
    graph = client.get(
        f"/api/v1/investigations/{investigation['id']}/graph", headers=admin["headers"]
    )
    assert graph.status_code == 200, graph.text
    assert len(graph.json()["nodes"]) == 2
    assert len(graph.json()["edges"]) == 1


def test_dashboard_and_collector_health(client, admin):
    entity(client, admin["headers"], "dashboard.example")
    dashboard = client.get("/api/v1/dashboard", headers=admin["headers"])
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["entity_total"] == 1
    collectors = client.get("/api/v1/operations/collectors", headers=admin["headers"])
    assert collectors.status_code == 200
    assert {item["name"] for item in collectors.json()} >= {
        "dns",
        "rdap",
        "certificate_transparency",
        "vulnerability",
    }
