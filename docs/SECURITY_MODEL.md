# Security Model

SignalGraph is a defensive, passive-first CTI platform. It is not an active scanner or exploitation framework.

## Authentication and authorization

- Passwords use Argon2id with memory-hard parameters.
- Browser sessions use short-lived signed bearer tokens stored in session storage.
- API operations do not rely on ambient cookies, so authenticated requests are not exposed to cookie-based CSRF.
- Roles are enforced server-side: viewers read, analysts manage intelligence and casework, administrators manage users and collector configuration.
- Access-control behavior is covered by API tests.
- First ownership is terminal-only. The frontend binds to loopback and web bootstrap is disabled, including on empty installations. Database locking serializes competing terminal setup commands.
- Login failures are limited per normalized account through atomic Redis accounting, default eight failures in fifteen minutes. Successful login clears that account's failure count. Hash leases limit concurrent checks to two across API processes. Missing users still take the Argon2 verification path.
- The supplied Nginx frontend additionally limits login requests per direct client IP to twelve per minute with a burst of four. It ignores visitor-supplied forwarding chains for this decision. Redis failure denies authentication temporarily rather than disabling limits. Failed-account keys use a keyed digest, not stored email addresses.
- Redis hash leases expire after thirty seconds to recover crashed workers. A hard two-check process semaphore still applies to stalled checks. The supplied two-worker API has a normal shared limit of two and a worst-case process ceiling of four stalled checks. Custom worker counts must budget two checks per process and verify normal hash latency fits the shared lease.

## Collector boundary and SSRF

Collectors construct requests from fixed, code-owned service origins. RDAP resolves its authoritative HTTPS service through the fixed [IANA bootstrap registries](https://data.iana.org/rdap/) using longest-prefix/suffix selection. Only an applicable registry-listed service can be queried. Credentials, nonstandard ports, local/private literal addresses and local hostnames are rejected. A submitted URL is never fetched directly. Redirect following remains disabled, including authoritative RDAP redirects to an unlisted destination. Unavailable services fail explicitly, never by fetching the submitted target. Observable values are validated and encoded before becoming query or path parameters.

## Browser protections

- React escapes displayed text by default; the application does not inject analyst HTML.
- Nginx sets a restrictive Content Security Policy and clickjacking, MIME-sniffing, referrer, and permissions headers.
- The API also emits defense-in-depth headers.

## Data and artifact handling

- SQLAlchemy parameterizes database queries.
- Pydantic validates and bounds API input.
- STIX uploads are content-type checked and limited to 5 MB and 10,000 objects.
- Collector responses are JSON-only, size bounded, hashed, and never executed.
- Transport checks reject oversized declared lengths and cap both streamed encoded and decoded bytes before JSON parsing. Only identity and bounded gzip encoding are accepted. Nesting and structural counts are limited before parsing, with a separate node-count check before downstream processing. The total HTTP budget covers retries, with a maximum one-second read wait between deadline checks. Retention/truncation metadata is separate from transport refusal.
- Raw responses and provenance remain access-controlled.

## Secrets

`.env` is excluded from Git. Production startup rejects the known development secret and requires a minimum-length replacement. Do not place API keys in collector notes or committed configuration.

## Deployment boundary

Keep PostgreSQL and Redis on the private Compose network. Terminate TLS at a trusted reverse proxy and restrict the loopback API port if remote API access is unnecessary.

Both published ports bind to loopback by default. If another proxy fronts Nginx, its peer address is the per-IP rate-limit identity unless the owner deliberately configures trusted `real_ip` sources at Nginx. Never trust an arbitrary visitor's X-Forwarded-For value or expose the direct API to bypass the frontend per-client limit. No remote service is deployed by these defaults.
