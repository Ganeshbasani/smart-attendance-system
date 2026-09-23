# AttendX — Attendance Intelligence & Early Intervention Platform

AttendX is a full-stack reference application that turns attendance from a passive record into a verified, explainable, predictive and actionable workflow. It is designed around the product direction in the supplied research brief: **Verified Attendance → Intelligence → Risk → Prediction → Early Warning → Recommended Action → Intervention → Outcome**.

## What changed from the original app

The original application was a Streamlit/CSV attendance tool. The upgraded product separates the experience into a modern React/TypeScript frontend and a FastAPI backend, with a normalized academic domain model and durable storage. Streamlit is no longer the primary application runtime.

### Core product capabilities

- Student: attendance runway, recovery math, risk explanations, projected semester-end attendance, QR scanning, offline queue state, notifications, correction requests and condonation workflow.
- Faculty: assigned subject/section access, live signed QR sessions, session history, student risk monitor, suspicious-session review and correction review.
- HOD: department risk distribution and intervention oversight.
- Admin: people/roster view, audit history, security posture and system health.
- Trust layer: HMAC-signed rotating QR payloads, short-lived tokens, registered browser-device verification, duplicate prevention and anomaly evidence.
- Offline-first path: PWA shell + IndexedDB event queue; attendance QR events can be reconciled after connectivity returns with idempotent client event IDs.
- Governance: audit events, correction requests, condonation requests and intervention lifecycle.
- Privacy: no mandatory face recognition or continuous location tracking.

## Architecture

```text
React + TypeScript + Vite + PWA shell
          │
          │ JSON/HTTP
          ▼
FastAPI + JWT + RBAC
          │
          ├── Attendance / QR / Device trust
          ├── Risk + Runway + Prediction
          ├── Notifications + Interventions
          ├── Correction / Condonation
          ├── Audit / Governance
          └── Sync / Reconciliation
          │
          ▼
SQLAlchemy
   ├── SQLite (local/demo)
   └── PostgreSQL (Docker / production path)
```

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### One-command Docker path

```powershell
docker compose up --build
```

Frontend: `http://localhost:5173`  \ Backend: `http://localhost:8000/docs`

## Demo accounts

The seed script creates these accounts:

| Username | Role | Password |
|---|---|---|
| student | Student | `AttendX@2026` |
| faculty | Faculty | `AttendX@2026` |
| hod | HOD | `AttendX@2026` |
| admin | Admin | `AttendX@2026` |

These are **demo credentials only**. Change them and set a long random `SECRET_KEY` before any real deployment.

## UI design principles

The interface intentionally avoids beginner-dashboard patterns: no neon palette, no oversized cards, no glassmorphism, no decorative AI widgets and no chart overload. The system uses a restrained light SaaS language, dense information hierarchy, responsive navigation, touch-friendly controls and decision-oriented cards.

The same application shell adapts for desktop, laptop, tablet and mobile. The student flow is optimized for phone scanning; faculty and admin flows remain usable on larger screens.

## Important implementation notes

- QR payloads are signed with a session secret and short-lived.
- Device identity is an opaque browser identifier, **not hardware attestation**.
- Offline QR attendance is reconciled server-side after reconnect. The server re-checks the signed token and limits delayed reconciliation to a short grace window.
- Anomaly detection flags evidence; it does not automatically punish students.
- The default reference build uses SQLite for zero-friction local development and PostgreSQL in Docker.
- File uploads are limited to common document/image types and 5 MB. For a real institution, use managed object storage and malware scanning.

## Validation

```powershell
cd backend
python -m compileall -q app
pytest -q
```

The automated tests cover authentication/RBAC boundaries and signed QR attendance with duplicate protection.
