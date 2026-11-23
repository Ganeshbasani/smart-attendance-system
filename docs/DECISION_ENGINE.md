# AttendX — Smart Attendance Decision Engine & Sessions (Phase 7)

**Status:** implemented (backend + live monitor). This describes actual behaviour.

## Decision engine (`backend/app/services/decision.py`)

A pure function `evaluate(...)` maps signals to one outcome. Thresholds are injected (env-configurable via `DECISION_MIN_CONFIDENCE` / `DECISION_MIN_QUALITY`, defaults 50 / 45). Deterministic policy order:

1. no active session → **REJECTED**
2. duplicate in session → **DUPLICATE**
3. spoof suspected → **REJECTED**
4. liveness not confirmed → **REJECTED**
5. confidence below threshold → **REVIEW_REQUIRED**
6. quality below threshold → **REVIEW_REQUIRED**
7. otherwise → **VERIFIED**

`MANUAL_OVERRIDE` is produced only by explicit staff action with a mandatory reason. The engine makes **no accuracy claims** — it applies policy to signals from the CV pipeline.

## Sessions (additive, `/api/v1/sessions`)

| Endpoint | Access | Purpose |
| --- | --- | --- |
| `GET /sessions` | any authenticated | list sessions (paged) |
| `POST /sessions` | admin/teacher | create (teacher: own classes only) |
| `GET /sessions/{id}` | any authenticated | get session |
| `POST /sessions/{id}/start` | owning teacher/admin | draft → active |
| `POST /sessions/{id}/stop` | owning teacher/admin | active → closed |
| `POST /sessions/{id}/decisions` | student (self) or staff | submit CV signals → decision |
| `GET /sessions/{id}/records` | any authenticated | decisions, optional `?decision=` filter |
| `GET /sessions/{id}/events` | any authenticated | polling feed (newest first) |
| `POST /sessions/{id}/manual` | owning teacher/admin | reasoned manual override |
| `POST /sessions/{id}/review/{student_id}` | owning teacher/admin | resolve a REVIEW_REQUIRED record |

New tables: `attendance_sessions`, `session_attendance` (unique `(session_id, user_id)`), `verification_events` (append-only inputs/outcomes, never raw biometrics). Migration `2b3c4d5e6f70`, single head. The legacy per-day `attendance` table and kiosk `/attendance/mark` flow are **unchanged**.

## Frontend live monitor (`/live`)

Session list, create/start/stop, 3-second polling of decisions + events, outcome counters, reasoned review and manual override dialogs, and a live camera preview. Verification submission takes **scanner-produced signals** (confidence, quality, liveness, spoof flag) — it does not fabricate CV results.

## Known limitations

- Multi-face detection/tracking, automatic frame selection, and automated PAD are not part of this phase; the camera preview is view-only and the monitor says so honestly.
- The verification form accepts precomputed signals; wiring automatic camera→CV→decision is a later integration step.
- Only owning teachers/admins can manage a session; students can submit only their own verification.
