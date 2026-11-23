# Project Audit

**Audit date:** 2026-11-22
**Scope:** `smart-attendance-system` repository at the current workspace HEAD, plus changes made during this upgrade.
**Method:** repository inventory and static inspection of app entry points, routes, models, migrations, CV/liveness services, frontend screens/API client, Docker/CI configuration, and tests. Automated tests were attempted; see Verification. This is not a penetration test or biometric accuracy study.

## Executive summary

AttendX is an existing React 18 + FastAPI attendance application, not a greenfield project. It already contains authentication, face enrollment/recognition, active head-turn liveness, daily attendance, academic records, role-based dashboards, session decisions, audit logging, analytics, migrations, Docker, and CI. Preserve these flows and continue with additive changes.

During this audit, a critical authorization gap was found in the session decision API: unauthenticated callers could submit outcomes for arbitrary user IDs, and reads of session records/events were not consistently scoped. Decision submission is now staff-only until scanner-device authentication exists; staff must manage the relevant session and class-linked targets must be enrolled. Students can view only their own session records; event feeds are staff-only; session lists/details are role-scoped. Regression tests cover anonymous/student submission and student event-feed access.

A separate multi-face service was added with SCRFD detector-only inference, Kalman prediction, two-stage high/low-confidence association, ephemeral IDs, quality-based frame selection, and ArcFace embedding extraction on selected frames. It is not yet connected to a camera UI or attendance endpoint and must be treated as an isolated scanner service, not as a shipped end-to-end feature.

## Application inventory

| Area | Current implementation |
|---|---|
| Frontend | React 18 JavaScript, MUI 5, CRA/Craco, React Router, Axios, Recharts, camera components, MediaPipe guidance, role dashboards, academic management, session live monitor |
| API | FastAPI, Pydantic v2, SQLAlchemy 2, synchronous ORM calls in async route handlers, legacy routes plus `/api/v1` aliases and native versioned academic/session routes |
| Authentication | JWT bearer auth, password hashing, admin/teacher/student checks; frontend API client adds bearer token |
| Recognition | InsightFace model pack, SCRFD detection + ArcFace embeddings, normalized cosine/k-NN matching, DB-backed embeddings and enrollment images |
| Liveness | Server-issued active head-turn challenge; client blink signal alone is not trusted. Passive PAD is not deployed |
| Persistence | PostgreSQL for production, SQLite for local development; Alembic migrations; academic and attendance-session tables |
| Operations | structured logging, request IDs, rate limiting, security headers, health/readiness checks, Docker Compose, CI |
| Deployment | README describes Vercel frontend, Render API, and Neon PostgreSQL; Docker Compose is available |

## Feature-by-feature matrix

| Feature | Status | Evidence / limitation |
|---|---|---|
| Registration, login, JWT, password hashing, account status | Implemented | Auth routes and security service; account deactivation checked during token resolution |
| Admin/teacher/student roles | Implemented | User role plus academic profile tables and role dependencies |
| Academic management | Implemented | Departments, academic sessions, courses, teachers, students, classes, enrollments; versioned API and admin screen |
| Daily attendance, checkout, shifts, leave, corrections | Implemented | Existing attendance and scheduling routes/models; preserve during session migration |
| Class attendance sessions | Implemented | Session lifecycle, decision engine, records, review, reasoned manual override |
| Session access control | Hardened in this change | Staff-only decision submission pending trusted scanner auth; student self-record reads; staff ownership and class enrollment checked; event feed staff-only |
| Face enrollment and identity matching | Implemented | InsightFace/ArcFace pipeline, gallery cache, configurable thresholds; no representative held-out accuracy report |
| Face quality | Partial | Existing blur/size/detection/brightness heuristics; new scanner quality score; pose/occlusion quality not yet integrated |
| Multi-face detection/tracking | Partial, service-only | New SCRFD detector-only path and ByteTrack-style tracker; no camera/UI/attendance integration, physical-camera validation pending |
| Passive PAD / RGB-IR | Not implemented | Prior candidate rejected after poor genuine-image behavior; no synchronized IR hardware or validated model |
| Offline event queue and batch synchronization | Not implemented | No durable edge queue, signed event protocol, or batch ingestion endpoint |
| pgvector/HNSW | Not implemented | Current matcher uses a process memory cache of vectors and cosine similarity; no measured need for another datastore yet |
| Device registry/heartbeat/metrics | Not implemented | No edge-device model or monitoring API |
| Consent, encrypted templates, retention enforcement | Incomplete | Biometric records include DB-stored vectors and enrollment images; no application-layer encryption or consent/retention workflow |
| Non-biometric fallback | Partial | Staff manual session override exists; user self-service equivalent path is not complete |
| Audit logging | Implemented | Audit model/service covers security and attendance actions; review scope for new routes remains ongoing |
| Analytics and CSV export | Implemented | Existing daily/weekly analytics and CSV route; no PDF reports or session/room analytics suite |
| WebSocket live updates | Not implemented | Live monitor polls the API; polling is adequate until measured otherwise |
| API versioning | Partial | Additive `/api/v1` aliases exist for legacy routers; not every route is natively versioned or grouped as `/v1/...` |
| Automated tests | Present, not run here | Backend/frontend test files and CI exist; local Python lacks `pytest-asyncio` and `cv2`, Docker command stalled |
| Performance report | Not available | No benchmark results were generated in this audit; hardware-specific targets remain unverified |

## Principal findings

1. **Session authorization:** the previously permissive session decision/read routes allowed cross-user actions/data exposure. The current change makes score-based submissions staff-only pending device auth and adds role/session scope. Regression tests were added but backend execution was unavailable locally.
2. **Biometric data protection:** embeddings and enrollment image bytes are stored in the application database without application-layer encryption, explicit consent lifecycle, or retention enforcement.
3. **Scaling state:** rate limiting and active-liveness challenges use process-local state; multi-worker deployments require shared state for consistent enforcement.
4. **CV claims:** the current web preview is not a multi-face tracker. The new service has not been exercised against a physical camera, enrolled gallery, held-out data, or presentation attacks.
5. **Session decision provenance:** the decision endpoint accepts client-provided scores/flags. Until the client is a trusted scanner or a server-owned CV service computes them, the endpoint must not be treated as proof of recognition/liveness. Authentication/scoping prevents arbitrary impersonation but does not make client-supplied scores trustworthy.
6. **Database architecture:** session decision tables exist, but device, consent, proximity, biometric-template separation, sync event, and anomaly-review structures are not present.
7. **Operational proof:** repository configuration supports local Docker and external deployment, but no live deployment, backup restore, physical device, or GPU was verified during this audit.

## Verification

- `python -m pytest tests/test_multiface.py tests/test_recognition_service.py -q` was attempted; collection stopped because `pytest_asyncio` is missing from the active Python environment.
- Importing the CV dependencies locally is unavailable because `cv2` is missing.
- `docker compose ps` did not return within the command wait window, so container-based test execution was not confirmed.
- `npm test -- --watchAll=false --runInBand --silent --forceExit LiveAttendance.test.js` passed (1 test). Jest reported that it force-exited due to an open handle; the full frontend suite/build was not run.
- Python bytecode compilation was run for the new service and tests.
- A dependency-light smoke script (with OpenCV stubbed; no actual detection/alignment model invoked) passed vector normalization, cosine matching, track confirmation/low-confidence recovery, and the 112×112 alignment adapter contract.
- `git diff --check` was run; trailing Markdown whitespace was corrected.
- No accuracy, FPS, latency, PAD error-rate, offline reconciliation, or deployment-health claims are made from this audit.

## Audit artifacts

- [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md) — architecture that exists now.
- [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) — staged remaining work.
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md) — security findings and controls.
- [FEATURE_STATUS.md](FEATURE_STATUS.md) — maintained capability matrix.
