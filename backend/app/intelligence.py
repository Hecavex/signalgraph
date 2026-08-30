from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

DOMAIN_RE = re.compile(r"^(?=.{1,253}\.?$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\.?$", re.I)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
HASH_RE = re.compile(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$")
CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.I)
ASN_RE = re.compile(r"^AS\d+$", re.I)
ALLOWED_TYPES = {
    "domain",
    "hostname",
    "ip_address",
    "url",
    "email_address",
    "file_hash",
    "file",
    "certificate",
    "asn",
    "organization",
    "malware",
    "threat_actor",
    "campaign",
    "infrastructure",
    "vulnerability",
    "attack_pattern",
    "report",
}


class ObservableError(ValueError):
    pass


def identify_type(value: str) -> str:
    candidate = value.strip()
    try:
        ipaddress.ip_address(candidate.strip("[]"))
        return "ip_address"
    except ValueError:
        pass
    if CVE_RE.fullmatch(candidate):
        return "vulnerability"
    if ASN_RE.fullmatch(candidate):
        return "asn"
    if HASH_RE.fullmatch(candidate):
        return "file_hash"
    if EMAIL_RE.fullmatch(candidate):
        return "email_address"
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() in {"http", "https"} and parsed.hostname:
        return "url"
    if DOMAIN_RE.fullmatch(candidate):
        return "domain"
    raise ObservableError("Unable to identify observable type; provide a supported explicit type")


def normalize_observable(value: str, entity_type: str | None = None) -> tuple[str, str]:
    raw = value.strip()
    if not raw or len(raw) > 2048 or any(ord(char) < 32 for char in raw):
        raise ObservableError("Observable is empty, too long, or contains control characters")
    detected = (entity_type or identify_type(raw)).lower()
    if detected not in ALLOWED_TYPES:
        raise ObservableError(f"Unsupported entity type: {detected}")

    if detected == "ip_address":
        normalized = str(ipaddress.ip_address(raw.strip("[]")))
    elif detected in {"domain", "hostname"}:
        hostname = raw.rstrip(".").lower()
        try:
            normalized = hostname.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ObservableError("Invalid internationalized domain") from exc
        if not DOMAIN_RE.fullmatch(normalized):
            raise ObservableError("Invalid domain or hostname")
    elif detected == "url":
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ObservableError("Only absolute HTTP and HTTPS URLs are accepted")
        try:
            host = parsed.hostname.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ObservableError("Invalid URL hostname") from exc
        port = f":{parsed.port}" if parsed.port else ""
        netloc = host + port
        normalized = urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))
    elif detected == "email_address":
        if not EMAIL_RE.fullmatch(raw):
            raise ObservableError("Invalid email address")
        local, domain = raw.rsplit("@", 1)
        normalized = f"{local}@{domain.encode('idna').decode('ascii').lower()}"
    elif detected == "file_hash":
        if not HASH_RE.fullmatch(raw):
            raise ObservableError("File hashes must be MD5, SHA-1, or SHA-256 hex values")
        normalized = raw.lower()
    elif detected == "vulnerability":
        if not CVE_RE.fullmatch(raw):
            raise ObservableError("Vulnerability identifiers must use CVE-YYYY-NNNN format")
        normalized = raw.upper()
    elif detected == "asn":
        if not ASN_RE.fullmatch(raw):
            raise ObservableError("ASN identifiers must use ASNNNN format")
        normalized = raw.upper()
    else:
        normalized = re.sub(r"\s+", " ", raw).strip()

    return detected, normalized
