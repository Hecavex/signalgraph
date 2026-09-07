# Compatibility

| Component | v1 development target |
| --- | --- |
| Python | 3.12 |
| Node.js | 22 LTS or 24 LTS |
| PostgreSQL | 16 |
| Redis | 7.4 |
| Docker Engine | 24+ |
| Docker Compose | v2 |
| Browsers | current and previous Chrome, Edge, Firefox; current Safari |
| OpenCTI / MISP | not part of v1 |

The Docker images are the reference environment. Compatibility is a verified claim only after the relevant CI and clean-start checks pass.

Runtime maintenance pins the Dockerfile image bytes for Python 3.12.14 (Bookworm), nginx 1.30.4 (Alpine), and the Node 22 build image. Docker Dependabot reviews run weekly. The required container gate scans the built API and frontend images for fixable HIGH/CRITICAL advisories before running the existing clean-stack checks. The scanner itself is pinned by version and image digest, uses exported images without Docker socket access, and runs only in disposable CI. No claim of a clean image is made until the exact-revision gate passes.

The nginx image contains an older libuuid package, so the Dockerfile explicitly upgrades it to Alpine 2.42.3-r1. Keep that temporary package pin under the same scheduled advisory gate until a reviewed nginx base includes the security rebuild. CI identified this package-level finding before release. It did not demonstrate an exploit against the application.
