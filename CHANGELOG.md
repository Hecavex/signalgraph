# Changelog

All notable changes to SignalGraph will be documented here. The project follows Semantic Versioning.

## [Unreleased]

### Added

- Recurring bounded v1 clean-stack assurance covering migrations, administrator creation, authentication, queue execution and the existing synthetic browser workflows.
- Hash-checked runtime, development and build dependency locks shared by CI and production containers.

- SignalGraph v1 application foundation with Docker Compose, FastAPI, React, PostgreSQL, Redis, Celery, and Alembic.
- Local authentication, role-based access control, audit events, and first-run administrator creation.
- Intelligence entities, observations, provenance, relationships, tags, confidence, and transparent risk scoring.
- Passive DNS, RDAP, Certificate Transparency, NVD, and optional URLScan collectors.
- Search, graph exploration, investigations, reports, import/export, operations, backup/restore, and synthetic demo data.
- Backend, frontend, integration, authorization, and browser workflow tests.
- Installation, user, API, security, operations, development, and compatibility documentation.
- Hecavex Internal Use and Security Research License 1.0, permitting internal organizational use and lawful security research while prohibiting resale, third-party services, and redistribution.
- GitHub issue forms, community and support guidance, citation metadata, dependency update configuration, and repository discovery badges.

### Changed

- CI diagnostics retain only allowlisted service status and synthetic failure screenshots, with authenticated traces excluded and a seven-day retention limit.

- Completed the local v1.0.0 release-candidate audit across backend, frontend, clean Compose deployment, browser workflows, PostgreSQL backup/restore, and runtime enrichment/retry behavior.
- Updated the jsdom test environment and removed the deprecated external Cytoscape type stub now that Cytoscape ships its own TypeScript declarations.

### Fixed

- Resolve authoritative RDAP services through IANA bootstrap data instead of rejecting the normal bootstrap redirect.

- Use a standards-valid synthetic administrator email in the demo and README capture workflow.
- Parse documented comma-separated `CORS_ORIGINS` values before Pydantic's complex-field decoding so clean production containers can start.
- Make collector-default initialization safe across concurrent API workers.
- Store Celery Beat runtime files in writable temporary storage and add worker/scheduler health checks.
- Preserve the analyst's collector selection through enrichment completion and job retry.

### Security

- Make initial administrator creation terminal-only and serialized, with loopback-only frontend publication.
- Add Redis-backed account throttling, concurrent password-check leases and per-client proxy login limits. Missing users perform password verification and unavailable rate-limit storage fails closed.
- Bound collector encoded/decoded transport bytes, JSON structure and total request deadlines before retaining or processing evidence.

- Require pytest 9.0.3 or newer in the development lock to address the reported [PYSEC-2026-1845 advisory](https://github.com/pypa/advisory-database/blob/main/vulns/pytest/PYSEC-2026-1845.yaml). Runtime dependencies are unchanged by this test-tool update.

### Deprecated

### Removed
