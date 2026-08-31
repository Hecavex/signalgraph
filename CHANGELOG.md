# Changelog

All notable changes to SignalGraph will be documented here. The project follows Semantic Versioning.

## [Unreleased]

### Added

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

- Completed the local v1.0.0 release-candidate audit across backend, frontend, clean Compose deployment, browser workflows, PostgreSQL backup/restore, and runtime enrichment/retry behavior.
- Updated the jsdom test environment and removed the deprecated external Cytoscape type stub now that Cytoscape ships its own TypeScript declarations.

### Fixed

- Use a standards-valid synthetic administrator email in the demo and README capture workflow.
- Parse documented comma-separated `CORS_ORIGINS` values before Pydantic's complex-field decoding so clean production containers can start.
- Make collector-default initialization safe across concurrent API workers.
- Store Celery Beat runtime files in writable temporary storage and add worker/scheduler health checks.
- Preserve the analyst's collector selection through enrichment completion and job retry.

### Security

### Deprecated

### Removed
