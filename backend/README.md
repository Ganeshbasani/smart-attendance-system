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
