# AttendX — Attendance Intelligence & Early Intervention Platform

AttendX has been upgraded from a lightweight Streamlit attendance manager into a portfolio-grade, real-world product centered on one idea:

> **Turn attendance from a passive record into an intelligent early-warning and intervention system.**

The product is deliberately built around **trust → intelligence → prediction → early action → explanation → outcome**.

## What changed from the original project

The original project was a useful prototype with Streamlit screens for student loading, attendance marking, analytics, and reports. Its README described CSV persistence and session-state authentication, and its reporting implementation generated random monthly/yearly values instead of calculating them from stored attendance records. The `requirements.txt` also listed only Streamlit even though the application imports Pandas and NumPy.

This version addresses those limitations while preserving the core attendance workflow.

| Current | Problem | Upgrade | Priority |
|---|---|---|---|
| CSV attendance storage | Fragile for multi-user, concurrent workflows | SQLite relational store with foreign keys, indexes, transactions and a Docker volume | P0 |
| Session-state-only login | Authentication state is not an application identity model | Users table, PBKDF2 password hashing, RBAC and failed-login throttling | P0 |
| One generic dashboard | Student/faculty/department/admin needs are different | Four role-specific workspaces | P0 |
| Present/Absent register | Passive record with little decision support | Attendance Runway + explainable Risk Engine + projection | P0 |
| Random monthly/yearly reporting | Not trustworthy | Reports calculate from persisted sessions and attendance records | P0 |
| Basic manual attendance | Proxy/screenshot abuse is not visible | Rotating signed QR, device identity, verification attempts and session anomaly review | P0 |
| No intervention workflow | Risk is detected too late | Recommendation + intervention tracker + notifications | P0 |
| No correction governance | Changes are hard to trace | Correction/condonation requests + audit trail | P1 |
| No recovery path for connection loss | Users can lose track of pending events | Idempotent offline JSON queue + sync/reconciliation screen | P1 |
| Dark/glass-heavy prototype styling | More visual than operational | Calm light SaaS design system, restrained color, hierarchy and responsive layout | P1 |
| No production guardrails | Hard to deploy or assess securely | Docker, CI, tests, Bandit, pip-audit, Trivy workflow, environment config | P1 |

## Flagship product capabilities

### 1. Attendance Runway

For every enrolled subject, AttendX calculates:

- current attendance
- classes conducted
- classes attended
- planned sessions remaining
- minimum future sessions required
- sessions that can still be missed
- mathematical recoverability
- maximum possible final attendance
- recent attendance rate
- trend in percentage points
- projected end-of-semester attendance
- near-term "next 7 sessions" requirement

The interface presents both a near-term action and a semester-level runway.

### 2. Explainable Risk Engine

Risk states are:

**Safe · Watch · At Risk · Critical**

Risk is based on attendance percentage, recent trend, consecutive absences, runway length, recovery possibility, projected outcome, and subject weight.

The product does not expose an opaque AI score. It shows the evidence behind a state.

### 3. Predictive Attendance

The projection uses a transparent deterministic rule:

> expected future attendance = current attendance + planned remaining sessions × recent attendance rate

That keeps the forecast understandable. ML can be added later only when sufficient historical data shows it improves prediction.

### 4. Layered anti-proxy verification

Faculty can open a session and display a short-lived signed QR token.

A student check-in passes through:

1. token signature validation
2. expiry validation
3. session-open validation
4. enrollment validation
5. duplicate protection
6. registered browser-device identity
7. auditable event recording

Verification attempts are stored so repeated expired/duplicate/invalid behavior can be reviewed.

### 5. Session anomaly detection

AttendX reviews a session for evidence such as:

- one device identity used across multiple students
- abnormal check-in bursts
- repeated rejected attempts
- duplicate attendance submissions

The workflow is intentionally:

**Suspicious session → evidence → review → human decision → audit trail**

An anomaly never automatically punishes a student.

### 6. Intelligent notifications

Notifications are stored in the database, ordered by priority, and deduplicated.

Example signals include:

- risk increased
- subject moved to Watch
- critical runway
- projected below threshold

### 7. Early intervention

Faculty can turn a risk signal into a trackable intervention:

**Detect → Explain → Notify → Recommend → Track**

The intervention has owner, status, due date, recommendation, notes and resolution timestamp.

### 8. Correction and condonation workflow

Students can submit:

- correction requests for a session
- condonation requests for a subject
- optional supporting documents

Faculty reviews requests and records the decision and review note.

Every decision is audited with:

**Who → Changed what → When → Why**

### 9. Offline-ready sync workflow

The Streamlit application cannot provide a full browser-PWA offline shell by itself, so this version does not pretend it can.

Instead, it provides a real reconciliation path:

- export a session queue as JSON
- keep the queue locally while connectivity is unavailable
- upload it through Sync Center after connectivity returns
- validate session/enrollment
- apply events idempotently using a client event ID
- record applied/rejected outcomes

The UI explicitly reports synchronization only after the server accepts the events.

### 10. Decision-based analytics

Charts and tables are tied to questions:

**Student:** What subject needs attention? What should I do next?

**Faculty:** Which students are becoming at risk? Which session needs review?

**HOD:** Which subjects/sections are deteriorating? Are interventions being resolved?

**Admin:** Where is risk rising? Is the system healthy? What policy is active?

## Roles

### Student
- Overview
- My Attendance
- Attendance Runway
- Risk explanation
- Verify Attendance
- Corrections / Condonation
- Notifications

### Faculty
- Overview
- Take Attendance
- Rotating QR sessions
- Faculty fallback
- Risk Monitor
- Session Review / anomaly evidence
- Corrections / Condonation review
- Sync Center
- Reports

### HOD
- Department overview
- Risk distribution
- Subject trend view
- Intervention tracker
- Department risk export

### Admin
- Institution overview
- Departments
- Roster import
- User administration
- Audit log
- System health
- Attendance policy configuration

## Demo accounts

These are development credentials only. Change them before any real deployment.

```text
Admin    : admin / admin123
HOD      : hod / hod123
Faculty  : faculty / faculty123
Student  : student1 / student123
Student2 : student2 / student123
```

## Local setup — Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:ATTENDX_SECRET_KEY = "replace-with-a-long-random-secret"
python seed.py
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

### One-command PowerShell helper

```powershell
.\run.ps1
```

The helper creates/uses the virtual environment, installs dependencies, seeds the demo database when needed, and starts Streamlit.

## Docker

Build and run:

```bash
docker compose up --build
```

The SQLite database is persisted through the `attendx_data` volume.

For production, set a real secret:

```bash
export ATTENDX_SECRET_KEY="a-long-random-secret"
docker compose up --build
```

## Tests

Core risk and authentication logic is covered by pytest.

```bash
pytest -q
```

Current local validation completed during the upgrade:

```text
5 passed
```

Static validation:

```bash
python -m compileall -q .
```

Security/quality checks used in CI:

```bash
python -m bandit -q -r . -x ./tests
pip-audit -r requirements.txt
```

## Architecture

```text
                 ┌───────────────────────────────┐
                 │           Streamlit UI          │
                 │ role-based workspaces           │
                 └──────────────┬────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
    Attendance Service     Risk / Runway          Workflows
          │                 Engine                  │
          │              Anomaly Rules              │
          └─────────────────────┬───────────────────┘
                                ▼
                         SQLite data layer
                                │
             ┌──────────────────┼─────────────────┐
             ▼                  ▼                 ▼
          Attendance         Audit             Sync Queue
          Sessions           Logs              Reconciliation
```

This is intentionally a **clean modular application**, not an unnecessary microservice estate.

## Data model

Core entities:

```text
users
students
subjects
enrollments
class_sessions
attendance_records
attendance_attempts
device_registrations
notifications
interventions
correction_requests
condonation_requests
sync_events
audit_logs
settings
```

## Privacy posture

AttendX avoids making face recognition, continuous GPS tracking, or biometrics mandatory.

For verification, the database stores an opaque hashed browser-device identity rather than the raw value.

The product only collects information required for the attendance workflow.

## Important production notes

This repository is designed to be **production-like and portfolio-grade**, but a real institution deployment should still add institution-specific infrastructure such as:

- SSO/OIDC
- centralized secret management
- managed PostgreSQL
- encrypted object storage for documents
- reverse proxy / TLS
- centralized logs and metrics
- backup/restore automation
- formal retention policies
- institution-specific approval rules
- configurable notification delivery (email/SMS)
- stronger device enrollment policy

The application deliberately avoids claiming that a Streamlit process is equivalent to a full enterprise identity platform.

## Research-driven product direction

The product direction follows the supplied research requirements around:

- Attendance Intelligence
- Attendance Runway
- Risk Engine
- Predictive Attendance
- Early Intervention
- Layered Anti-Proxy Verification
- Session Anomaly Detection
- Intelligent Notifications
- Decision-based Analytics
- Privacy-conscious attendance
- Offline-first attendance
- Professional SaaS UX

The unifying product question is:

> **What happened? → Why is it happening? → What will happen next? → Who needs to know? → What should they do?**

## Repository structure

```text
AttendX-Intelligence-Platform/
├── app.py
├── auth.py
├── config.py
├── db.py
├── seed.py
├── requirements.txt
├── run.ps1
├── Dockerfile
├── docker-compose.yml
├── .streamlit/
│   └── config.toml
├── .github/
│   └── workflows/
│       └── ci.yml
├── data/
│   ├── students.csv
│   ├── attendance.csv
│   └── documents/
├── services/
│   ├── anomaly.py
│   ├── attendance_service.py
│   ├── interventions.py
│   ├── notifications.py
│   ├── reports.py
│   ├── risk_engine.py
│   ├── sync.py
│   └── workflows.py
├── tests/
│   ├── test_auth.py
│   └── test_risk_engine.py
├── screenshots/
└── docs/
    └── ARCHITECTURE.md
```

## Product identity

**AttendX** is no longer positioned as “an attendance register.”

It is positioned as:

> **Attendance Intelligence & Early Intervention Platform**

The strongest portfolio story is that the system moves from:

**Verified Attendance → Intelligence → Risk Detection → Prediction → Early Warning → Recommended Action → Intervention → Improved Outcome**
