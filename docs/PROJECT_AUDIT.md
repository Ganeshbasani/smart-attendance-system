# AttendX — Project Audit

**Audit date:** 2026-11-20
**Scope:** `N:\Smart attendence\smart-attendance-system` (branch `upgrade/production-hardening`, HEAD `f62d3f2`)
**Method:** static repository inspection (files, models, routers, services, config, tests, CI, Docker) plus the existing test baseline. **No source files were modified during the audit.**
**Checkpoint:** clean working tree at `f62d3f2`; this is the pre-implementation Git checkpoint.

---

## 0. CRITICAL SCOPE DISCREPANCY — READ FIRST

The master prompt describes an **existing Streamlit application** ("Existing Streamlit application", "Existing Python modules", "CSV data handling"). The repository contains **no Streamlit code at all** (grep for `streamlit` / `st.title` / `st.button` returns zero matches). The actual application is:

- **Frontend:** React 18 (JavaScript, not TypeScript), MUI 5, CRA + Craco, React Router, Recharts, framer-motion, react-webcam, MediaPipe Tasks Vision, axios.
- **Backend:** FastAPI 0.104 + Pydantic v2 + SQLAlchemy 2 + Alembic, InsightFace (SCRFD detector + ArcFace `w600k_r50` embeddings), onnxruntime (CPU-capable), OpenCV.

**All findings below describe the repository as it actually exists.** If the Streamlit app lives in a different repository, that repository must be supplied before this audit can apply to it. Confirmation is required before implementation begins.

A prior, separately-approved hardening program (Phases 1–7) is already committed on this branch: security baseline, attendance domain (shifts/leave/corrections), AI/ML observability, notifications, analytics, frontend productionization, and DevOps. This audit treats that as the baseline; it is **not** redone here.

---

## 1. Current architecture (summary)

```
Browser (React 18 + MUI, CRA/Craco build)
   |  axios, JWT in localStorage, REACT_APP_API_URL (default http://localhost:8000)
   v
FastAPI app (app/main.py)
   |  middleware: CORS, security headers, request-id/context, rate limiting, audit
   v
Routers -> Services -> SQLAlchemy models -> PostgreSQL (prod) / SQLite (dev)
                     -> InsightFace (lazy-loaded FaceAnalysis, CPU by default)
                     -> OpenCV quality checks + active head-turn liveness
```

Deployment: frontend on Vercel (`frontend/vercel.json` SPA rewrites), backend on Render, database on Neon (per `README.md`); Docker Compose full stack also provided. Backend image runs as non-root `appuser` with model pre-downloaded. CI: GitHub Actions (backend tests + single-Alembic-head check; frontend tests + `CI=true` build).

---

## 2. Existing feature inventory

| Feature | Status | Evidence |
|---|---|---|
| JWT auth, password hashing, RBAC (admin/user) | **Working** | `auth.py`, `core/security.py`, `deps.py` |
| User registration / profile / change password | **Working** | `auth.py`, `users.py` |
| Face enrollment (multi-image, DB-backed embeddings + images) | **Working** | `face.py`, `face_recognition.py`, `FaceEmbedding`/`FaceImage` |
| Cosine similarity + k-NN voting, configurable threshold | **Working** | `face_recognition.py`, config thresholds, `scripts/benchmark_thresholds.py` |
| Quality screening (blur, face size, detection score, min encodings) | **Working (single face, heuristic)** | `face_recognition.check_image_quality` |
| Active liveness (server-issued head-turn challenge, geometric yaw check) | **Working (single face, in-memory store)** | `services/liveness.py` |
| Multi-frame agreement before marking + anti-replay frame difference | **Working** | `attendance.py`, config `ATTENDANCE_MIN_*` |
| Automatic attendance mark / checkout | **Working** | `POST /attendance/mark`, `/checkout` |
| One attendance record per user per day (DB unique constraint) | **Working** | migration `7c9e1f4b2a81` |
| Admin mark-present / bulk update / correction approval | **Working** | `admin.py`, `POST /mark-present`, `PUT /attendance/{id}` |
| Shift scheduling, holidays, leave requests, correction requests | **Working** | `scheduling.py`, models in `models/scheduling.py` |
| Shift-aware punctuality, leave/holiday-aware analytics, anomaly listing | **Working** | `services/analytics.py`, `routers/analytics.py` |
| CSV export (stdlib csv writer) | **Working** | `GET /analytics/export` |
| In-app notifications + optional email (stdlib smtplib) | **Working** | `notifications.py`, `services/notifications.py` |
| Audit log (auth/admin/face/attendance actions) | **Working** | `services/audit.py`, `AuditLog` model |
| Request correlation IDs, security headers, rate limiting | **Working** | `core/request_context.py`, `main.py`, `core/limiter.py` |
| Health (`/health`) and readiness (`/ready`, DB-backed) | **Working** | `main.py` |
| Alembic migrations (6, single head `d4e5f6a7b8c9`) | **Working** | `alembic/versions/`, CI head check |
| Backend tests (183) / frontend tests (5) / CI build | **Working** | `backend/tests/`, `src/*.test.js`, `ci.yml` |
| Docker (non-root backend, nginx frontend, compose, healthchecks) | **Working** | Dockerfiles, `docker-compose.yml`, `nginx.conf` |

---

## 3. Missing features (master prompt vs repository)

| # | Required | Status | Notes |
|---|---|---|---|
| 1 | Three roles: admin / teacher / student | **Missing** | only `admin` / `user` (`role = Column(String, default="user")`) |
| 2 | Students, teachers, departments, courses, classes, enrollments tables | **Missing** | `users` is the sole identity table |
| 3 | Attendance sessions (create/start/stop, active-session enforcement) | **Missing** | attendance is per-user-per-day, not per-session |
| 4 | Multi-face detection + bounding boxes + landmarks | **Partial** | InsightFace detector finds multiple faces, but code selects only the **largest** face (`_largest_face`) |
| 5 | Multi-face tracking (ByteTrack), temporary IDs, occlusion handling | **Missing** | no tracker, no frame-to-frame identity |
| 6 | Quality assessment: pose, occlusion, brightness, contrast, confidence | **Partial** | blur/size/det-score only; no pose/occlusion/brightness/contrast scoring |
| 7 | Passive AI anti-spoofing (MiniFASNet / Silent-FAS) | **Missing / rejected** | `liveness.py` documents evaluation: candidate model classified all 64 real photos as spoof → would lock out users. Active head-turn challenge used instead. |
| 8 | Central smart attendance decision engine with VERIFIED/REVIEW_REQUIRED/REJECTED/DUPLICATE/MANUAL_OVERRIDE | **Partial** | decisions are spread across routers; no unified engine or outcome vocabulary |
| 9 | Offline-first SQLite event queue, idempotent batch ingest, backoff, recovery | **Missing** | none |
| 10 | WebSocket live attendance monitoring | **Missing** | no WebSocket anywhere |
| 11 | Student/teacher/admin portals with class management | **Partial** | admin + generic user dashboards only |
| 12 | Consent records, retention policies, biometric encryption at rest, separation of PII/templates | **Partial** | face delete/revocation + audit exist; embeddings/images stored raw in DB, no consent/retention tables, no encryption-at-rest |
| 13 | Non-biometric attendance fallback | **Missing** | none |
| 14 | Anomaly detection (duplicates, conflicts, failures, unusual corrections) | **Partial** | rule-based anomaly *listing* exists; no dedicated anomaly records/review queue |
| 15 | Versioned `/api/v1/*` API | **Missing** | routes are unversioned (e.g. `/auth/login`, `/attendance`) |
| 16 | TypeScript + Vite + Tailwind | **Missing** | JS + CRA/Craco + MUI (prompt says "where appropriate" — migration is a decision, see Technical Decisions) |
| 17 | Playwright E2E, Ruff | **Missing** | Pytest + React Testing Library only |
| 18 | `docs/*` documentation set | **Missing** | only `README.md` and `backend/README.md` existed before this audit |
| 19 | Performance report with real measurements | **Missing** | none |

---

## 4. Technical risks

1. **Scope mismatch (highest risk):** the prompt targets a Streamlit codebase that does not exist here. Proceeding without confirmation could implement against the wrong baseline.
2. **Biometric privacy:** raw ArcFace embeddings and enrollment images are stored in the database unencrypted; no consent/retention machinery. High sensitivity under India's DPDP Act.
3. **In-memory state:** rate limiter and liveness challenge store are per-process — multi-worker/replica deployments break both.
4. **Active liveness limits:** head-turn challenge stops photos/stills/non-matching replays, but not a real-time pose-controllable puppet; documented in `liveness.py`. No passive PAD model currently usable (evaluation failed).
5. **Threshold calibration:** `FACE_MATCH_THRESHOLD=0.42` etc. were tuned with `scripts/benchmark_thresholds.py`, but no representative validation dataset/results are committed — accuracy cannot be claimed.
6. **Frontend run-state:** the frontend production build is currently served on port 3000 with no backend on 8000, producing "Connection error: Network Error" on login. This is a runtime configuration issue, not an application bug.
7. **Legacy compatibility:** adding sessions/classes/roles must not break the existing per-day attendance, leave/correction workflows, or existing user data.
8. **Dependency security:** 35 transitive npm advisories (0 critical) remain in the CRA dev toolchain.
9. **Deployment:** live Render backend URL previously returned 503; deploy verification needs credentials/dashboard access.

---

## 5. Dependencies that can be reused

- `insightface`, `onnxruntime`, `opencv-python`, `numpy` — detection + embeddings + CV quality checks (already CPU-capable; SCRFD detector is part of the model pack).
- `sqlalchemy`, `alembic`, `psycopg2-binary` — schema extension and migrations.
- `slowapi`, `passlib[bcrypt]`, `python-jose` — auth/security.
- `pytest`, React Testing Library — existing test harnesses.
- `stdlib csv`, `smtplib` — export/notification without new deps.
- `@mediapipe/tasks-vision` — browser-side landmarks (currently blink challenge).
- Docker/GitHub Actions infrastructure already in place.

## 6. Modules that require new code

Multi-face detector wrapper + tracker (ByteTrack or a simple centroid/IoU tracker), quality scorer (pose/brightness/contrast/occlusion), decision engine, session & academic-domain models/routers, offline event queue + idempotent batch API, WebSocket broadcaster, consent/retention/encryption layer, non-biometric check-in, anomaly record/review queue, 3-role authorization layer, API v1 prefix/aliases, new documentation set, Playwright suite, performance instrumentation.

---

## 7. Verdict

The repository is a **substantial, working two-role attendance system** with solid backend engineering, real InsightFace recognition, an unconventional but documented active-liveness defence, and a modern React/MUI frontend. It is **not** a Streamlit app, and roughly half of the master prompt's features are genuinely missing. The audit recommends **incremental extension of this codebase** (preserving all existing features and data) rather than a rewrite, with explicit decisions on the role model, sessions, multi-face pipeline, and passive anti-spoofing before implementation. See `IMPLEMENTATION_ROADMAP.md` and `TECHNICAL_DECISIONS.md`.
