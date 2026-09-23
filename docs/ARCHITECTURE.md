# AttendX Architecture Notes

## Application boundary

The app uses one Streamlit process and one SQLite database. Business logic is separated into service modules so the application can later move to PostgreSQL or a dedicated API without rewriting the product logic.

## Layers

### UI
`app.py` owns navigation, role-aware presentation, forms, tables and charts.

### Services
`services/attendance_service.py`
- attendance sessions
- signed QR token generation/validation
- student verification
- attendance recording
- subject statistics

`services/risk_engine.py`
- runway mathematics
- deterministic risk state
- explainable signals

`services/anomaly.py`
- session-level evidence checks

`services/notifications.py`
- priority ordering
- deduplication

`services/interventions.py`
- intervention lifecycle

`services/workflows.py`
- correction/condonation governance

`services/sync.py`
- idempotent offline queue reconciliation

`services/reports.py`
- query-backed reporting

### Data
`db.py` owns SQLite schema, connection handling, transactions, settings and audit entries.

## Security controls

- PBKDF2 password hashing with per-password salts
- constant-time digest comparison
- failed-login throttling
- parameterized SQL
- SQLite foreign keys
- unique constraints on attendance
- signed short-lived QR tokens
- opaque hashed browser identity
- audit trail
- Streamlit XSRF protection enabled in config
- security checks in CI

## Attendance trust model

```text
Faculty opens session
        ↓
Short-lived signed QR token
        ↓
Student submission
        ↓
Token validation
        ↓
Enrollment validation
        ↓
Duplicate validation
        ↓
Registered browser-device check
        ↓
Attendance record
        ↓
Attempt trail + audit
        ↓
Session anomaly review
```

## Why deterministic intelligence first?

Attendance eligibility has clear mathematical rules. A transparent formula is preferable to an ML model where the model adds no decision value.

ML becomes appropriate when the application has enough real history to answer questions such as:
- probability of future absence
- intervention response likelihood
- course-level deterioration forecasting

Those can be added as separate predictive models without replacing the transparent runway calculation.

## Migration path

For an actual institutional rollout:

1. Replace SQLite with PostgreSQL.
2. Move document storage to encrypted object storage.
3. Add OIDC/SSO.
4. Put the application behind TLS and a reverse proxy.
5. Move audit/log data to centralized infrastructure.
6. Add scheduled backup and restore validation.
7. Add email/SMS notification providers.
8. Add a real client-side offline PWA if true offline capture is mandatory.
9. Add integration tests against production-equivalent infrastructure.
