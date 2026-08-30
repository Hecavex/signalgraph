# API

The versioned API is rooted at `/api/v1`. Interactive OpenAPI documentation is served from `/api/docs` by the API service.

## Authentication

```http
POST /api/v1/auth/login
Content-Type: application/json

{"email":"analyst@example.org","password":"..."}
```

Use the returned token as `Authorization: Bearer <token>`.

## Core resources

| Resource | Purpose |
| --- | --- |
| `/auth` | first administrator, login, current user, user administration |
| `/entities` | normalized intelligence, enrichment, notes, relationships |
| `/graph/{entity_id}` | bounded neighbor expansion and filters |
| `/investigations` | casework, evidence, timeline, assessment, export |
| `/reports` | analyst reports and Markdown export |
| `/operations` | collector health/configuration, jobs, retries, audit log |
| `/exchange` | JSON, CSV, STIX 2.1 import/export |
| `/dashboard` | platform statistics and recent/high-risk intelligence |

Error responses use HTTP status codes and a JSON `detail` field. Validation failures return 422. Authentication and authorization failures return 401 and 403 respectively.
