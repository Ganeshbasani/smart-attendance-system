---
title: Smart Attendance System API
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# Smart Attendance System — Backend API

FastAPI service for face-recognition attendance, powered by InsightFace
(ArcFace, 512-d embeddings) on onnxruntime (CPU). The backend is stateless:
face embeddings and enrollment images are stored in the database, so it
survives restarts and redeploys.

## Runtime configuration (environment variables)

| Variable | Description | Example |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy DSN. SQLite locally, PostgreSQL in production. | `postgresql+psycopg2://user:pass@host/db?sslmode=require` |
| `SECRET_KEY` | JWT signing key (>= 32 chars). Required when `DEBUG=false`. | output of `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ADMIN_EMAIL` | Email that is granted the admin role on registration. | `you@example.com` |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed origins. | `https://your-app.vercel.app` |
| `DEBUG` | `true` for local dev (relaxes secret check). | `false` |

Schema is managed by Alembic and applied automatically at startup.

## Academic domain & API v1 (AttendX Phase 2)

Additive endpoints under **`/api/v1`** introduce the academic domain without
changing any legacy route. All previous paths (e.g. `/auth/login`,
`/attendance`) keep working; identical aliases are available under
`/api/v1/auth/login`, `/api/v1/attendance`, etc.

**Roles:** `admin`, `teacher`, `student`. Legacy accounts with role `user`
were migrated to `student`; permission checks still accept `user` wherever
`student` is expected. New registrations receive `student` by default;
`ADMIN_EMAIL` still receives `admin`.

**Endpoints (admin-only mutations; authenticated reads):**

| Resource | Paths |
| --- | --- |
| Departments | `GET/POST /api/v1/departments`, `PUT/DELETE /api/v1/departments/{id}` |
| Academic sessions | `GET/POST /api/v1/academic-sessions`, `PUT/DELETE /api/v1/academic-sessions/{id}` |
| Courses | `GET/POST /api/v1/courses`, `PUT/DELETE /api/v1/courses/{id}` |
| Teachers | `GET/POST /api/v1/teachers`, `GET/PUT/DELETE /api/v1/teachers/{id}` |
| Students | `GET/POST /api/v1/students`, `GET/PUT/DELETE /api/v1/students/{id}`, `GET /api/v1/students/me` |
| Classes | `GET/POST /api/v1/classes`, `GET/PUT/DELETE /api/v1/classes/{id}` |
| Enrollment | `GET /api/v1/classes/{id}/students`, `POST /api/v1/classes/{id}/enrollments`, `DELETE /api/v1/classes/{id}/enrollments/{student_id}` |

List endpoints accept `?skip=0&limit=50` (limit max 200). Students see only
their own profile and enrolled classes; teachers can read academic data but
cannot perform admin mutations. Every mutation writes an `audit_logs` row
with an `academic.*` action. Duplicate unique fields return 409; missing
referenced IDs return 404.

Creating a teacher or student also creates the underlying `users` account
(hashed password, unique ID); deleting the profile deletes that user and
its related data via database cascades.

## Notifications

Decision events create an in-app notification for the affected user
(`notifications` table): leave approve/reject, attendance-correction
approve/reject, and shift assignment changes. Users read them at
`GET /notifications` (plus `/unread-count`, `/{id}/read`, `/read-all`),
always scoped to the authenticated user; the navbar bell shows the badge.

Email is an optional secondary channel, **off by default**: set
`EMAIL_NOTIFY_ENABLED=true` and `SMTP_*` (see `.env.example`) to send a copy.
Sending uses the standard library (`smtplib`), is synchronous with a short
timeout, and is best-effort — a failure is logged and never fails the request.
`NOTIFICATIONS_ENABLED=false` turns the whole feature off.

## Analytics

`/analytics/*` endpoints (admin-only) compute every metric from real
attendance rows — nothing is simulated. Since Phase 5 they are aware of the
scheduling domain:

* **Punctuality is shift-aware** — the `is_late` flag written at mark time
  (shift start + grace) is preferred; only rows from users without a shift
  fall back to the legacy 09:00 rule.
* **Approved leave is not absence** — users on approved leave are excluded
  from expected-people denominators (`absentToday`, per-day attendance %).
* **Holidays are flagged, not scored** — on a holiday `expectedToday`/daily
  `expected` is 0 and rows carry `holiday`/`holidayName`, so charts can gap
  the day instead of plotting a false 0%.
* CSV export uses the stdlib `csv` writer (correct quoting);
  `/analytics/anomalies` validates `days` (1–366) and `severity`
  (`all|high|medium|low`).

## Face recognition tuning & calibration

All effective values are logged once at startup (`Face/liveness config: ...`),
so a process's gallery and liveness rules are visible in the logs.

### Changing the model pack

`FACE_MODEL_PACK` selects the InsightFace pack used for detection and
embeddings. Every stored enrollment records the pack it was computed with, and
only matching rows load into the recognition gallery — mixing packs would put
vectors from different spaces into one cosine search. After a pack change,
affected users must re-register their face:

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/admin/face/model-status
```

The response reports configured model, matching/stale row counts, and the
`stale_users` list. The admin Face Management page shows the same information
as a status line.

### Measuring match thresholds

`FACE_MATCH_THRESHOLD` (0.42) and `FACE_DUPLICATE_THRESHOLD` (0.50) are
operating points, not accuracy claims. To measure false-accept/false-reject
rates on **your own** labeled photos (one subfolder per person):

```bash
# from backend/, with a representative sample of your deployment's images
python -m scripts.benchmark_thresholds --dataset path/to/labeled/photos
```

The sweep reports FAR/FRR per threshold, the equal-error-rate point, and how
the configured thresholds score on that data. The repository ships no labeled
dataset, so the tool evaluates only what you supply — it prints no numbers
until then. Nothing is changed automatically; pick a threshold from your own
trade-off and set it explicitly.

### Calibrating the liveness direction sign

The capture path mirrors frames (the webcam preview and react-webcam
screenshots are flipped), so whether a correct "turn left" measures as
increasing or decreasing yaw is convention-dependent. Direction enforcement
(`LIVENESS_REQUIRE_DIRECTION`) therefore ships **off**; the sweep-magnitude
check (which blocks static photos) is sign-independent and always on.

Both directional extents are logged on every attempt (`yaw_directional`,
`yaw_directional_opposite`). Measure the actual convention from real capture
logs:

```bash
python -m scripts.calibrate_direction path/to/backend.log
# or: docker logs <backend> 2>&1 | python -m scripts.calibrate_direction -
```

The tool recommends `LIVENESS_DIRECTION_SIGN=1` or `-1` once it has enough
real attempts (default 10), and refuses to recommend anything otherwise. After
setting the sign, enable `LIVENESS_REQUIRE_DIRECTION=true`. Only real capture
attempts through the webcam flow are valid calibration data.

## Local development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
docker build -t attendance-api .
docker run -p 8000:8000 --env-file .env attendance-api
```

Interactive API docs are served at `/docs`.
