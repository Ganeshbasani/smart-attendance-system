# Security Audit

**Review date:** 2026-11-22  
**Scope:** static code/configuration review of authentication, session routes, face handling, database, deployment files, and logging. This is not a penetration test, cryptographic review, legal opinion, or external infrastructure assessment.

## Findings

| Severity | Finding | State / evidence | Recommended action |
|---|---|---|---|
| High | Session decision submission previously allowed anonymous attribution to arbitrary user IDs | Fixed in this change: score-based endpoint is staff-only, requires the session manager, and checks class enrollment for class-linked decisions. Regression tests added. | Run regression suite and add device-authenticated scanner submissions before automated attendance trusts submitted scores. |
| High | Session records and event feeds previously lacked consistent class/role scope | Fixed in this change: session list/detail and records are scoped; students see only their own records; verification event feed is staff-only and session manager scoped. Regression coverage is partial. | Add teacher/student cross-class integration tests and periodic authorization review for every new endpoint. |
| High | Biometric data is sensitive and stored without application-level encryption | Open: face embeddings and enrollment image bytes are persisted in DB. | Separate templates from profile data; use managed envelope encryption, restricted access, key rotation, consent, retention, deletion, and backup controls. |
| High | Session decision signals can be client supplied | The live-monitor form that allowed staff to type confidence/liveness values was removed. The API still accepts these fields from an authenticated session owner, so auth/scope does not prove signals came from a trusted recognizer. | Require a server-owned CV pipeline or a device-authenticated and signed scanner assertion scoped to an active roster/session. Never treat browser-provided booleans as proof. |
| Medium | Rate limiting and liveness challenges use process-local state | Open: state is not shared across multiple workers/replicas. | Use a shared store or enforce single-worker deployment until shared semantics exist. |
| Medium | JWT bearer token is held by the frontend API client in browser storage | Review needed: possession of token grants account access; XSS exposure depends on app defenses and deployment. | Assess CSP/XSS surface; consider secure HttpOnly cookie architecture if appropriate, including CSRF design. |
| Medium | Default local/compose secrets are weak placeholders | Production config validates `SECRET_KEY`; compose has developer defaults. | Use managed deployment secrets, reject weak production secrets, and avoid sharing non-local compose deployments with defaults. |
| Medium | Enrollment images are retained with embeddings | Open: retention and withdrawal process is incomplete. | Minimize imagery, define purpose-specific retention, implement deletion and audit, and ensure backup expiration is understood. |
| Medium | API uses async route declarations with synchronous ORM sessions | Open: can block event loop under load; not a direct vulnerability. | Measure first; migrate to async DB stack or synchronous routes/thread handling if API load requires it. |
| Low | API versioning is additive/inconsistent | Open: legacy routes are mounted with `/api/v1` aliases while some routers are native versioned. | Normalize docs and schemas; preserve aliases until clients migrate. |
| Low | Physical camera, edge-device authentication, and network controls were not validated | Open: no device registry or mTLS deployment evidence. | Complete hardware/device threat model and deployment tests before edge rollout. |

## Existing controls observed

- JWT auth, password hashing, active-account checks, and admin/teacher/student role dependencies.
- Rate limiting, CORS origin configuration, request IDs, security headers, HSTS outside debug mode, and centralized error responses.
- Database uniqueness constraints for daily attendance and one record per user/session.
- Audit/verification records for key admin and attendance actions.
- Readiness endpoint verifies database access; production secret validation rejects weak keys.
- Face APIs generally return match results rather than raw template vectors.
- Active liveness challenge is server issued; client blink flags alone are not treated as authoritative in the legacy kiosk flow.

## Immediate response and validation

The session-route authorization gaps were corrected in `backend/app/api/routers/sessions.py`. Added tests assert anonymous and student decision submission are denied and a student cannot access the session event feed. The live monitor's manual CV-signal entry was removed and its camera preview is labeled view-only. The focused frontend test passes; backend tests were not executable locally because `pytest_asyncio` and OpenCV are missing; see [PROJECT_AUDIT.md](PROJECT_AUDIT.md). These code changes still require CI confirmation before release.

## Release blockers for a real biometric production rollout

1. Consent, withdrawal, retention, and template deletion are implemented and reviewed.
2. Template encryption and key lifecycle are tested; access is limited to the recognition path.
3. Automated decisions cannot rely on untrusted client scores or booleans.
4. Cross-class authorization tests pass on PostgreSQL-backed integration tests.
5. Secrets, TLS, backups/restores, deployment logs, and incident response are reviewed for the actual hosting environment.
6. Recognition and liveness performance/error rates are measured on representative, consented data and named hardware.

## Limits

No live service, cloud account, production database, device fleet, source control secret store, or network configuration was accessed for this review. Findings are based on repository code/configuration only.
