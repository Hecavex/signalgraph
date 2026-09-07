from __future__ import annotations

import ipaddress
from urllib.parse import quote, urlsplit


def bootstrap_kind(value: str, entity_type: str) -> tuple[str, str, str]:
    if entity_type in {"domain", "hostname"}:
        name = value.rstrip(".").encode("idna").decode("ascii").lower()
        if "/" in name or ":" in name or not name or "." not in name:
            raise ValueError("Invalid RDAP domain")
        return "dns", "domain", name
    if entity_type == "ip_address":
        address = ipaddress.ip_address(value)
        if not address.is_global:
            raise ValueError("RDAP only supports public IP resources")
        return f"ipv{address.version}", "ip", str(address)
    if entity_type == "asn":
        identifier = value.upper().removeprefix("AS")
        if not identifier.isdigit() or not 1 <= int(identifier) <= 4_294_967_295:
            raise ValueError("Invalid RDAP ASN")
        return "asn", "autnum", str(int(identifier))
    raise ValueError("Unsupported RDAP resource")


def authoritative_url(payload: dict | list, kind: str, route: str, identifier: str) -> str:
    """Select only a service provided by the fixed HTTPS IANA bootstrap registry."""
    if not isinstance(payload, dict) or not isinstance(payload.get("services"), list):
        raise ValueError("Invalid IANA RDAP bootstrap registry")
    matches: list[tuple[int, str]] = []
    for service in payload["services"]:
        if not isinstance(service, list) or len(service) != 2:
            raise ValueError("Malformed IANA RDAP service")
        ranges, bases = service
        if not isinstance(ranges, list) or not isinstance(bases, list):
            raise ValueError("Malformed IANA RDAP service lists")
        for resource in ranges:
            specificity = -1
            if kind == "dns":
                suffix = str(resource).lower()
                if identifier == suffix or identifier.endswith("." + suffix):
                    specificity = len(suffix)
            elif kind in {"ipv4", "ipv6"}:
                network = ipaddress.ip_network(resource)
                if ipaddress.ip_address(identifier) in network:
                    specificity = network.prefixlen
            elif kind == "asn":
                low, separator, high = str(resource).partition("-")
                start, end = int(low), int(high if separator else low)
                if start <= int(identifier) <= end:
                    specificity = 4_294_967_296 - (end - start)
            if specificity >= 0:
                matches.extend((specificity, base) for base in bases if isinstance(base, str))
    for _, base in sorted(matches, key=lambda match: -match[0]):
        try:
            parsed = urlsplit(base)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.port not in {None, 443}
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
                or "\\" in base
                or parsed.hostname.endswith((".localhost", ".local", ".internal"))
                or "." not in parsed.hostname
            ):
                continue
            try:
                literal = ipaddress.ip_address(parsed.hostname)
            except ValueError:
                literal = None
            if literal is not None and not literal.is_global:
                continue
            if not parsed.path.endswith("/") or "/../" in parsed.path:
                continue
            return base + route + "/" + quote(identifier, safe="")
        except ValueError:
            continue
    raise ValueError("No approved HTTPS IANA RDAP service for this resource")
