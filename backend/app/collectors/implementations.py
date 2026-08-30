from __future__ import annotations

from urllib.parse import quote, urlencode

import dns.resolver

from app.collectors.base import CollectedRelation, Collector, CollectorResult
from app.config import get_settings


class DNSCollector(Collector):
    name = "dns"
    supported_types = frozenset({"domain", "hostname"})
    source_url = "dns://system-resolver"

    def collect(self, value: str, entity_type: str, timeout: float) -> CollectorResult:
        records: dict[str, list[str]] = {}
        relations: list[CollectedRelation] = []
        resolver = dns.resolver.Resolver(configure=True)
        resolver.lifetime = timeout
        for record_type in ("A", "AAAA", "CNAME", "MX", "NS"):
            try:
                answers = resolver.resolve(value, record_type, raise_on_no_answer=False)
            except (
                dns.resolver.NXDOMAIN,
                dns.resolver.NoAnswer,
                dns.resolver.NoNameservers,
                dns.exception.Timeout,
            ):
                continue
            values: list[str] = []
            for answer in answers:
                target = str(answer).rstrip(".")
                if record_type == "MX":
                    target = str(answer.exchange).rstrip(".")
                values.append(target)
                relation_type = (
                    "resolves_to" if record_type in {"A", "AAAA"} else f"dns_{record_type.lower()}"
                )
                relation_entity_type = "ip_address" if record_type in {"A", "AAAA"} else "hostname"
                relations.append(
                    CollectedRelation(
                        target, relation_entity_type, relation_type, 80, {"record": record_type}
                    )
                )
            if values:
                records[record_type] = sorted(set(values))
        return CollectorResult(self.name, self.source_url, 200, records, {"records": records}, relations)


class RDAPCollector(Collector):
    name = "rdap"
    supported_types = frozenset({"domain", "hostname", "ip_address", "asn"})
    source_url = "https://rdap.org"

    def collect(self, value: str, entity_type: str, timeout: float) -> CollectorResult:
        route = "domain" if entity_type in {"domain", "hostname"} else "ip"
        identifier = value
        if entity_type == "asn":
            route, identifier = "autnum", value.removeprefix("AS")
        url = f"{self.source_url}/{route}/{quote(identifier, safe='')}"
        status, payload = self.request_json(url, timeout)
        observations = {
            key: payload.get(key)
            for key in ("handle", "name", "startAddress", "endAddress", "country", "port43", "events")
            if isinstance(payload, dict) and payload.get(key) is not None
        }
        relations: list[CollectedRelation] = []
        if isinstance(payload, dict):
            for entity in payload.get("entities", []):
                if isinstance(entity, dict) and entity.get("handle"):
                    relations.append(
                        CollectedRelation(str(entity["handle"]), "organization", "registered_by", 55)
                    )
        return CollectorResult(self.name, url, status, payload, observations, relations)


class CertificateTransparencyCollector(Collector):
    name = "certificate_transparency"
    supported_types = frozenset({"domain", "hostname"})
    source_url = "https://crt.sh"

    def collect(self, value: str, entity_type: str, timeout: float) -> CollectorResult:
        query = urlencode({"q": value, "output": "json"})
        url = f"{self.source_url}/?{query}"
        status, payload = self.request_json(url, timeout)
        rows = payload[:200] if isinstance(payload, list) else []
        relations: list[CollectedRelation] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            cert_id = str(row.get("id") or row.get("serial_number") or "")
            if cert_id and cert_id not in seen:
                seen.add(cert_id)
                relations.append(
                    CollectedRelation(
                        cert_id,
                        "certificate",
                        "observed_in_certificate",
                        70,
                        {"issuer": row.get("issuer_name")},
                    )
                )
            for name in str(row.get("name_value", "")).splitlines():
                clean = name.lstrip("*.").rstrip(".").lower()
                if clean and clean != value and clean not in seen:
                    seen.add(clean)
                    relations.append(CollectedRelation(clean, "domain", "shares_certificate", 65))
        observations = {
            "certificate_count": len(rows),
            "truncated": isinstance(payload, list) and len(payload) > 200,
        }
        return CollectorResult(self.name, url, status, rows, observations, relations)


class VulnerabilityCollector(Collector):
    name = "vulnerability"
    supported_types = frozenset({"vulnerability"})
    source_url = "https://services.nvd.nist.gov"

    def collect(self, value: str, entity_type: str, timeout: float) -> CollectorResult:
        query = urlencode({"cveId": value})
        url = f"{self.source_url}/rest/json/cves/2.0?{query}"
        status, payload = self.request_json(url, timeout)
        vulnerabilities = payload.get("vulnerabilities", []) if isinstance(payload, dict) else []
        observations: dict = {"cve": value, "result_count": len(vulnerabilities)}
        if vulnerabilities:
            cve = vulnerabilities[0].get("cve", {})
            observations["published"] = cve.get("published")
            observations["last_modified"] = cve.get("lastModified")
            observations["weaknesses"] = cve.get("weaknesses", [])
            observations["metrics"] = cve.get("metrics", {})
            descriptions = cve.get("descriptions", [])
            observations["description"] = next(
                (item.get("value") for item in descriptions if item.get("lang") == "en"), None
            )
        return CollectorResult(self.name, url, status, payload, observations)


class URLScanCollector(Collector):
    name = "urlscan"
    supported_types = frozenset({"domain", "hostname", "ip_address", "url"})
    source_url = "https://urlscan.io"

    def collect(self, value: str, entity_type: str, timeout: float) -> CollectorResult:
        settings = get_settings()
        field = {"ip_address": "ip", "url": "page.url"}.get(entity_type, "domain")
        query = urlencode({"q": f"{field}:{value}", "size": 25})
        url = f"{self.source_url}/api/v1/search/?{query}"
        headers = {"API-Key": settings.urlscan_api_key} if settings.urlscan_api_key else None
        status, payload = self.request_json(url, timeout, headers=headers)
        results = payload.get("results", []) if isinstance(payload, dict) else []
        relations: list[CollectedRelation] = []
        for row in results:
            page = row.get("page", {}) if isinstance(row, dict) else {}
            domain = page.get("domain")
            ip = page.get("ip")
            if domain and domain != value:
                relations.append(CollectedRelation(domain, "domain", "seen_in_urlscan", 50))
            if ip and ip != value:
                relations.append(CollectedRelation(ip, "ip_address", "seen_in_urlscan", 50))
        return CollectorResult(self.name, url, status, payload, {"result_count": len(results)}, relations)
