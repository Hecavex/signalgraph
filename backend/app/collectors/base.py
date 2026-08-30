from __future__ import annotations

import hashlib
import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def request_json(
        self, url: str, timeout: float, headers: dict[str, str] | None = None
    ) -> tuple[int, dict | list]:
        # URLs are constructed only by concrete collectors from allowlisted fixed origins.
        with httpx.Client(timeout=timeout, follow_redirects=False, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, (dict, list)):
                raise ValueError("Collector returned unsupported JSON")
            return response.status_code, payload

    @abstractmethod
    def collect(self, value: str, entity_type: str, timeout: float) -> CollectorResult:
        raise NotImplementedError
