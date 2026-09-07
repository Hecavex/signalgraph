import gzip
import json
import socket
import threading
import time

import httpx
import pytest

from app.collectors.implementations import RDAPCollector, VulnerabilityCollector
from app.collectors.rdap_bootstrap import authoritative_url, bootstrap_kind
from app.config import get_settings


class BytesStream(httpx.AsyncByteStream):
    def __init__(self, chunks, tick=None):
        self.chunks = chunks
        self.yielded = 0
        self.tick = tick

    async def __aiter__(self):
        for chunk in self.chunks:
            if self.tick:
                self.tick()
            self.yielded += len(chunk)
            yield chunk


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        "app.collectors.base.httpx.AsyncClient",
        lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler)),
    )


def json_response(payload):
    return httpx.Response(200, stream=BytesStream([json.dumps(payload).encode()]))


def test_declared_oversize_rejected_before_body_read(monkeypatch):
    monkeypatch.setattr(get_settings(), "raw_response_max_bytes", 1000)
    stream = BytesStream([b"x" * 1100])
    transport(
        monkeypatch, lambda request: httpx.Response(200, headers={"Content-Length": "1100"}, stream=stream)
    )
    with pytest.raises(ValueError, match="transport limit"):
        VulnerabilityCollector().request_json("https://services.nvd.nist.gov/test", 2)
    assert stream.yielded == 0


@pytest.mark.parametrize("encoding", ["identity", "gzip"])
def test_chunked_and_compressed_oversize_rejected_before_json_parse(monkeypatch, encoding):
    monkeypatch.setattr(get_settings(), "raw_response_max_bytes", 1000)
    data = json.dumps({"value": "x" * 5000}).encode()
    wire = gzip.compress(data) if encoding == "gzip" else data
    stream = BytesStream([wire[i : i + 128] for i in range(0, len(wire), 128)])
    transport(
        monkeypatch,
        lambda request: httpx.Response(200, headers={"Content-Encoding": encoding}, stream=stream),
    )
    parsed = []
    monkeypatch.setattr("app.collectors.base.json.loads", lambda body: parsed.append(body))
    with pytest.raises(ValueError, match="transport limit"):
        VulnerabilityCollector().request_json("https://services.nvd.nist.gov/test", 2)
    assert parsed == []
    if encoding == "identity":
        assert stream.yielded < len(wire)


@pytest.mark.parametrize("encoding", ["identity", "gzip"])
def test_normal_bounded_json_retains_payload(monkeypatch, encoding):
    expected = {"handle": "SYNTHETIC", "events": [{"eventAction": "registration"}]}
    data = json.dumps(expected).encode()
    wire = gzip.compress(data) if encoding == "gzip" else data
    transport(
        monkeypatch,
        lambda request: httpx.Response(
            200, headers={"Content-Encoding": encoding}, stream=BytesStream([wire])
        ),
    )
    assert VulnerabilityCollector().request_json("https://services.nvd.nist.gov/test", 2) == (200, expected)


@pytest.mark.parametrize("body", [b"[" * 34 + b"0" + b"]" * 34, b"[0,1,2,3,4,5]"])
def test_structural_limits_precede_expensive_processing(monkeypatch, body):
    monkeypatch.setattr(get_settings(), "collector_max_json_nodes", 4)
    transport(monkeypatch, lambda request: httpx.Response(200, stream=BytesStream([body])))
    with pytest.raises(ValueError, match="limit exceeded"):
        VulnerabilityCollector().request_json("https://services.nvd.nist.gov/test", 2)


def test_slow_trickle_has_one_total_deadline(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("app.collectors.base.time.monotonic", lambda: clock[0])

    def tick():
        clock[0] += 0.6

    stream = BytesStream([b"[", b"0", b"]"], tick)
    transport(monkeypatch, lambda request: httpx.Response(200, stream=stream))
    with pytest.raises(httpx.TimeoutException, match="total deadline"):
        VulnerabilityCollector().request_json("https://services.nvd.nist.gov/test", 1)
    assert stream.yielded == 2


@pytest.mark.parametrize(
    ("value", "entity_type", "kind", "resource", "route", "identifier"),
    [
        ("example.com", "domain", "dns", "com", "domain", "example.com"),
        ("8.8.8.8", "ip_address", "ipv4", "8.0.0.0/8", "ip", "8.8.8.8"),
        ("2001:4860::8888", "ip_address", "ipv6", "2001:4860::/32", "ip", "2001:4860::8888"),
        ("AS15169", "asn", "asn", "15160-15170", "autnum", "15169"),
    ],
)
def test_real_bootstrap_boundary_uses_only_selected_iana_service(
    monkeypatch,
    value,
    entity_type,
    kind,
    resource,
    route,
    identifier,
):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.host == "data.iana.org":
            return json_response({"services": [[[resource], ["https://rdap.example.org/service/"]]]})
        return json_response({"handle": "SYNTHETIC", "entities": []})

    transport(monkeypatch, handler)
    result = RDAPCollector().collect(value, entity_type, 5)
    assert calls[0] == f"https://data.iana.org/rdap/{kind}.json"
    assert len(calls) == 2 and calls[1].startswith(f"https://rdap.example.org/service/{route}/")
    assert result.request_url == calls[1]
    assert result.observations["bootstrap_registry"] == calls[0]
    assert bootstrap_kind(value, entity_type) == (kind, route, identifier)


@pytest.mark.parametrize(
    "base",
    [
        "http://rdap.example.org/",
        "https://127.0.0.1/",
        "https://[::1]/",
        "https://10.0.0.1/",
        "https://rdap.local/",
        "https://rdap.internal/",
        "https://user:pass@rdap.example.org/",
        "https://rdap.example.org:65536/",
        "https://rdap.example.org/?url=",
        "https://rdap.example.org/#x",
    ],
)
def test_unapproved_rdap_destinations_fail_closed(base):
    with pytest.raises(ValueError, match="No approved"):
        authoritative_url({"services": [[["com"], [base]]]}, "dns", "domain", "example.com")


def test_authoritative_redirect_is_not_followed(monkeypatch):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.host == "data.iana.org":
            return json_response({"services": [[["com"], ["https://rdap.example.org/"]]]})
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/private"})

    transport(monkeypatch, handler)
    with pytest.raises(httpx.HTTPStatusError):
        RDAPCollector().collect("example.com", "domain", 5)
    assert len(calls) == 2


@pytest.mark.parametrize("phase", ["headers", "body"])
def test_real_socket_trickle_deadline_closes_transport(phase, monkeypatch):
    # Local synthetic socket only: each chunk arrives well inside the inactivity
    # timeout, but the complete response never arrives within the total budget.
    # This HTTP-only loopback test must not load the host certificate store or
    # use deployment proxy settings; production TLS verification is unchanged.
    original = httpx.AsyncClient
    monkeypatch.setattr(
        "app.collectors.base.httpx.AsyncClient",
        lambda **kwargs: original(**kwargs, verify=False, trust_env=False),
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(3)
    port = listener.getsockname()[1]
    closed = threading.Event()
    stop = threading.Event()

    def serve():
        try:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(0.03)
                connection.recv(4096)
                prefix = b"HTTP/1.1 200 OK\r\n"
                if phase == "body":
                    prefix += b"Content-Length: 100000\r\n\r\n["
                connection.sendall(prefix)
                while not stop.wait(0.05):
                    try:
                        connection.sendall(b"X-Test: a\r\n" if phase == "headers" else b" ")
                        if connection.recv(1) == b"":
                            closed.set()
                            return
                    except TimeoutError:
                        pass
                    except OSError:
                        closed.set()
                        return
        finally:
            listener.close()

    server = threading.Thread(target=serve, daemon=True)
    server.start()
    started = time.monotonic()
    try:
        with pytest.raises(httpx.TimeoutException, match="total deadline"):
            VulnerabilityCollector().request_json(f"http://127.0.0.1:{port}/synthetic", 0.5)
        assert time.monotonic() - started < 1.5
        assert closed.wait(1), "Cancelled request left its transport open"
    finally:
        stop.set()
        server.join(3)
    assert not server.is_alive()
