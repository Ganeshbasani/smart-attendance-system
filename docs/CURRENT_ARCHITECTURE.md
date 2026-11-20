# AttendX — Current Architecture (as audited 2026-11-20)

This document describes the system **as it exists at audit time**, not the target design.

## 1. Repository layout

```
smart-attendance-system/
├── .github/workflows/ci.yml       # backend tests + alembic head check + frontend tests + CI build
├── .env.example                   # root compose substitution template
├── docker-compose.yml             # postgres + backend + nginx frontend
├── README.md                      # product/overview/deployment documentation
├── backend/
│   ├── Dockerfile                 # python:3.11-slim, model pre-download, non-root appuser
│   ├── README.md                  # env vars, notifications, analytics, face tuning
│   ├── requirements.txt
│   ├── alembic.ini + alembic/versions/   # 6 migrations, single head d4e5f6a7b8c9
│   ├── scripts/                   # benchmark_thresholds, calibrate_direction, migrate_faces_to_db
│   ├── tests/                     # 18 test modules (183 tests)
│   └── app/
│       ├── main.py                # app factory, lifespan, middleware, /health, /ready
│       ├── core/                  # config, security, limiter, logging, request_context, uploads, time_utils
│       ├── db/                    # session (run_migrations), base
│       ├── models/                # user, attendance, face, audit, notifications, scheduling
│       ├── schemas/               # user, attendance, scheduling
│       ├── services/              # face_recognition, liveness, analytics, audit, notifications, scheduling
│       └── api/                   # deps.py + routers/ (auth, users, attendance, face, admin,
│                                  #   admin_scheduling, user_scheduling, analytics, notifications, liveness)
└── frontend/
    ├── Dockerfile                 # node:18-alpine build -> nginx:alpine
    ├── nginx.conf                 # SPA fallback, immutable /static/, no-cache index.html, security headers
    ├── vercel.json                # SPA rewrites
    ├── public/                    # index.html (Inter + Roboto fonts), favicon, manifest
    └── src/
        ├── index.js               # theme (MUI), BrowserRouter, CssBaseline; ErrorBoundary inside App
        ├── App.js                 # AuthContext, routes, nav layout
        ├── services/api.js        # axios instance, JWT interceptor, API_BASE_URL from REACT_APP_API_URL
        └── components/            # 18 components (Home, Login, Register, FaceCapture, FaceCamera,
                                   #   MarkAttendance, dashboards, profile, attendance, analytics, etc.)
```

## 2. Layer diagram

```
┌──────────────────────────────────────────────────────────────┐
│ Browser                                                      │
│  React 18 + MUI 5 · react-router · Recharts · framer-motion   │
│  react-webcam · MediaPipe FaceLandmarker (blink challenge)    │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTPS/HTTP · axios · JSON · Bearer JWT
┌───────────────────────────▼──────────────────────────────────┐
│ FastAPI (app/main.py)                                        │
│  CORS · security headers · X-Request-ID · slowapi · audit log │
│  lifespan: validate_security -> mkdirs -> run_migrations()    │
├──────────────────────────────────────────────────────────────┤
│ Routers (unversioned paths)                                  │
│  /auth /users /attendance /face /admin /analytics             │
│  /liveness /notifications /shifts /holidays /leave-requests   │
├──────────────────────────────────────────────────────────────┤
│ Services                                                     │
│  FaceRecognitionService (InsightFace, cosine+kNN)             │
│  LivenessService (server-issued head-turn challenge)          │
│  AnalyticsService (shift/leave/holiday aware)                 │
│  AuditService · NotificationService · SchedulingService       │
├──────────────────────────────────────────────────────────────┤
│ SQLAlchemy 2 models + Alembic migrations                      │
│  users · attendance · face_embeddings · face_images           │
│  audit_logs · notifications · shifts · holidays               │
│  leave_requests · attendance_correction_requests              │
└───────────────────────────┬──────────────────────────────────┘
                            │ PostgreSQL (prod, Neon) / SQLite (local default)
```

## 3. Data model (existing tables)

| Table | Purpose | Key constraints |
|---|---|---|
| `users` | identity + `role` (`admin` / `user`) + shift assignment | unique email |
| `attendance` | per-user daily mark, in/out, punctuality flag | **unique (user_id, date)** |
| `face_embeddings` | 512-d ArcFace vectors, one row per enrollment image | FK user, model version |
| `face_images` | enrollment image bytes in DB | FK user |
| `audit_logs` | actor, action, target, timestamp, metadata | indexed |
| `notifications` | user-scoped, read state, event type | FK user |
| `shifts` / `holidays` | scheduling context | — |
| `leave_requests` / `attendance_correction_requests` | approval workflows with reasons | FK user |

## 4. Key request flows

**Enrollment:** browser captures N faces (MediaPipe-driven guidance) → `POST /face/register/{user_id}` → server quality-checks each frame, extracts 512-d embeddings, stores embeddings + image bytes in DB (no disk files). Admin enrollment currently bypasses the active liveness challenge.

**Mark attendance:** client runs MediaPipe blink/liveness heuristics and captures frames → `POST /attendance/mark` with files, client liveness flag, anti-replay frame difference → server-side active liveness challenge (head-turn yaw sweep) → face recognition against DB gallery → quality/confidence gates → creates/updates one `attendance` row for the day.

**Analytics:** routers call `AnalyticsService`, which prefers the stored `is_late` flag (shift-aware), excludes approved leave and holidays from expected-people denominators, and computes daily/weekly trends and department totals. CSV export uses `csv.writer`.

## 5. AI/ML pipeline (current)

```
camera frames (browser)
  -> MediaPipe FaceLandmarker (blink guidance, client side)
  -> uploaded JPEG frames
  -> InsightFace SCRFD detector + ArcFace w600k_r50 (512-d, normalized)
  -> largest face only, per frame
  -> OpenCV quality (blur variance, min face size, detection score)
  -> active liveness: server-issued random left/right head-turn challenge,
     re-detect frames, measure yaw sweep + sign (single-use, in-memory, TTL 90s)
  -> cosine similarity vs all per-user embeddings, k-NN voting, threshold
  -> attendance decision in router
```

There is **no** multi-face tracker, no passive PAD/MiniFASNet, no per-frame quality scoring for pose/brightness/occlusion, and no WebSocket stream.

## 6. Configuration surface

`backend/app/core/config.py` (Pydantic Settings, env-driven): `DEBUG`, `SECRET_KEY`, `DATABASE_URL`, `BACKEND_CORS_ORIGINS`, rate limits, `FACE_MODEL_PACK` (buffalo_l), `FACE_USE_GPU` (default false), `FACE_MATCH_THRESHOLD` (0.42), `FACE_DUPLICATE_THRESHOLD` (0.50), `FACE_KNN_K` (5), quality thresholds, liveness challenge/geometry settings, attendance anti-replay settings, audit/notification/ SMTP options. Production (`DEBUG=false`) refuses weak `SECRET_KEY` at startup.

## 7. Deployment topology

- **Frontend:** static build on Vercel with SPA rewrites (`vercel.json`), or nginx container from `frontend/Dockerfile`.
- **Backend:** Render (per README) or `backend/Dockerfile` image; `$PORT` respected; `/ready` healthcheck; migrations run at startup.
- **DB:** Neon PostgreSQL in production; SQLite default for local dev.
- **CI:** pushes to `main` and `upgrade/production-hardening`; PRs to `main`.
- **Local:** `docker compose up --build` with root `.env` (see `.env.example`) exposes frontend :3000 and API :8000.

## 8. Known architectural constraints

- Per-process in-memory rate limiter and liveness challenge store (break with multiple workers).
- Single-face pipeline; identity is locked to the authenticated user at mark time.
- Raw biometric embeddings/images stored in DB (no encryption-at-rest or consent records).
- Unversioned API paths; no pagination on several list endpoints.
- Frontend env is build-time (`REACT_APP_API_URL`), so changing the API target requires a rebuild.
