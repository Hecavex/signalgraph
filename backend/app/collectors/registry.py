from __future__ import annotations

from app.collectors.base import Collector
from app.collectors.implementations import (
    CertificateTransparencyCollector,
    DNSCollector,
    RDAPCollector,
    URLScanCollector,
    VulnerabilityCollector,
)

COLLECTORS: dict[str, Collector] = {
    collector.name: collector
    for collector in (
        DNSCollector(),
        RDAPCollector(),
        CertificateTransparencyCollector(),
        VulnerabilityCollector(),
        URLScanCollector(),
    )
}


def get_collector(name: str) -> Collector:
    try:
        return COLLECTORS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown collector: {name}") from exc


def collector_names() -> list[str]:
    return sorted(COLLECTORS)
