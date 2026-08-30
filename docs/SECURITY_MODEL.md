# Security Model

SignalGraph is a defensive, passive-first CTI platform. It is not an active scanner or exploitation framework.

## Authentication and authorization

- Passwords use Argon2id with memory-hard parameters.
- Browser sessions use short-lived signed bearer tokens stored in session storage.
- API operations do not rely on ambient cookies, so authenticated requests are not exposed to cookie-based CSRF.
- Roles are enforced server-side: viewers read, analysts manage intelligence and casework, administrators manage users and collector configuration.
- Access-control behavior is covered by API tests.

## Collector boundary and SSRF

Collectors construct requests only from fixed, code-owned service origins. A submitted URL is never fetched directly. Redirect following is disabled for collector HTTP requests. Observable values are validated and encoded before becoming query or path parameters.

## Browser protections

- React escapes displayed text by default; the application does not inject analyst HTML.
- Nginx sets a restrictive Content Security Policy and clickjacking, MIME-sniffing, referrer, and permissions headers.
- The API also emits defense-in-depth headers.

## Data and artifact handling

- SQLAlchemy parameterizes database queries.
- Pydantic validates and bounds API input.
- STIX uploads are content-type checked and limited to 5 MB and 10,000 objects.
- Collector responses are JSON-only, size bounded, hashed, and never executed.
- Raw responses and provenance remain access-controlled.

## Secrets

`.env` is excluded from Git. Production startup rejects the known development secret and requires a minimum-length replacement. Do not place API keys in collector notes or committed configuration.

## Deployment boundary

Keep PostgreSQL and Redis on the private Compose network. Terminate TLS at a trusted reverse proxy and restrict the loopback API port if remote API access is unnecessary.
