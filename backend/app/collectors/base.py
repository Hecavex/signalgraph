from __future__ import annotations

import hashlib
import json
import threading
import time
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import get_settings


@dataclass
class CollectedRelation:
    value: str
    entity_type: str | None
    relation_type: str
    confidence: int = 60
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectorResult:
    collector: str
    request_url: str
    status_code: int
    payload: dict | list
    observations: dict[str, Any]
    relations: list[CollectedRelation] = field(default_factory=list)

    @property
    def sha256(self) -> str:
        canonical = json.dumps(self.payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(canonical).hexdigest()


class Collector(ABC):
    name: str
    supported_types: frozenset[str]
    source_url: str
    _rate_lock = threading.Lock()
    _last_request: dict[str, float] = {}

    def supports(self, entity_type: str) -> bool:
        return entity_type in self.supported_types

    def throttle(self, per_minute: int) -> None:
        interval = 60.0 / max(per_minute, 1)
        with self._rate_lock:
            elapsed = time.monotonic() - self._last_request.get(self.name, 0.0)
            if elapsed < interval:
                time.sleep(interval - elapsed)
            self._last_request[self.name] = time.monotonic()

    def request_json(
        self, url: str, timeout: float, headers: dict[str, str] | None = None
    ) -> tuple[int, dict | list]:
        # URLs are constructed only by concrete collectors from allowlisted fixed origins.
        deadline = time.monotonic() + timeout
        for attempt in range(3):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise httpx.TimeoutException("Collector total deadline exceeded")
            try:
                # Allow the remaining budget for initial response headers, then
                # bound body-read waits separately so slow chunks cannot reset it.
                limits = httpx.Timeout(remaining)
                request_headers = {"Accept-Encoding": "gzip, identity", **(headers or {})}
                with (
                    httpx.Client(
                        timeout=limits,
                        follow_redirects=False,
                        headers=request_headers,
                    ) as client,
                    client.stream("GET", url) as response,
                ):
                    response.raise_for_status()
                    response.request.extensions["timeout"]["read"] = min(
                        max(deadline - time.monotonic(), 0.001), 1.0,
                    )
                    payload = _bounded_json(response, deadline)
                    return response.status_code, payload
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 2 or time.monotonic() >= deadline:
                    raise
                time.sleep(min(0.25 * (attempt + 1), max(deadline - time.monotonic(), 0)))
        raise AssertionError("Unreachable collector retry state")

    @abstractmethod
    def collect(self, value: str, entity_type: str, timeout: float) -> CollectorResult:
        raise NotImplementedError


def _bounded_json(response: httpx.Response, deadline: float) -> dict | list:
    settings = get_settings()
    cap = settings.raw_response_max_bytes
    declared = response.headers.get("content-length")
    if declared is not None and (not declared.isdigit() or int(declared) > cap):
        raise ValueError("Collector response exceeds transport limit or has invalid length")
    encoding = response.headers.get("content-encoding", "identity").strip().lower()
    if encoding not in {"identity", "gzip"}:
        raise ValueError("Unsupported collector content encoding")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
    body = bytearray()
    wire_bytes = 0
    for chunk in response.iter_raw():
        if time.monotonic() >= deadline:
            raise httpx.TimeoutException("Collector total deadline exceeded")
        wire_bytes += len(chunk)
        if wire_bytes > cap:
            raise ValueError("Collector encoded response exceeds transport limit")
        decoded = decoder.decompress(chunk, cap - len(body) + 1) if decoder else chunk
        if len(body) + len(decoded) > cap:
            raise ValueError("Collector decoded response exceeds transport limit")
        body.extend(decoded)
    if decoder and (not decoder.eof or decoder.unused_data or decoder.unconsumed_tail):
        raise ValueError("Invalid or concatenated compressed collector response")
    if time.monotonic() >= deadline:
        raise httpx.TimeoutException("Collector total deadline exceeded")
    # Bound structural depth before invoking the recursive JSON parser. Quotes
    # and escapes prevent brackets inside string values from affecting depth.
    depth = 0
    structural_items = 0
    quoted = escaped = False
    for char in body:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            structural_items += 1
            if depth > settings.collector_max_json_depth:
                raise ValueError("Collector JSON nesting limit exceeded")
        elif char in (93, 125):
            depth -= 1
        elif char == 44:
            structural_items += 1
        if structural_items > settings.collector_max_json_nodes:
            raise ValueError("Collector JSON structural limit exceeded")
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, (dict, list)):
        raise ValueError("Collector returned unsupported JSON")
    pending = [payload]
    nodes = 0
    while pending:
        value = pending.pop()
        nodes += 1
        if nodes > settings.collector_max_json_nodes:
            raise ValueError("Collector JSON node limit exceeded")
        if isinstance(value, dict):
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return payload
