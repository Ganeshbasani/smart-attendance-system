# Technical Decisions

This page records decisions reflected in the current repository and the boundaries for the remaining upgrade. Earlier planning-only approvals are superseded by the implemented code and this project audit.

## Decisions in force

### Keep the current application stack

Extend React 18 + MUI + CRA/Craco and FastAPI + SQLAlchemy + Alembic. A frontend/backend rewrite would add migration risk without improving attendance correctness by itself.

### Keep InsightFace/ArcFace for the current recognition path

The current gallery uses normalized embeddings from a configured InsightFace pack. Do not mix embeddings from different model packs. Add another recognition model only after a documented comparison on representative, held-out data.

### Keep active server-issued liveness; do not claim passive PAD

The active head-turn challenge is the current server-side check. The browser blink result is guidance only. Passive PAD and RGB-IR remain research until model licensing, target-sensor integration, genuine-user testing, and presentation-attack testing are complete.

### Keep legacy daily attendance and add session attendance

The daily uniqueness rule and legacy routes remain for compatibility. Class sessions have separate attendance rows, decision outcomes, audit events, and a unique `(session_id, user_id)` constraint.

### Preserve additive `/api/v1` migration

Legacy routes remain mounted while aliases/native versioned routes are introduced. A route is not considered fully migrated until schemas, auth, pagination, and tests agree.

### Multi-face tracking stays isolated until scanner trust is defined

The new SCRFD + two-stage Kalman/IoU tracker module has process-local ephemeral track IDs. It does not yet submit attendance, perform a trusted roster match, or connect to a camera worker. Integrate only after device/user authentication, room/session scope, and capture/privacy boundaries are defined.

### Keep PostgreSQL as the source of truth; defer pgvector

Current enrollment galleries are matched from a process-local NumPy cache. Do not add pgvector/HNSW until a measured gallery size, selective-filter query, or latency requirement justifies it. If templates are encrypted at the application layer, ordinary vector distance operations cannot be assumed to work over ciphertext.

### Require a reasoned non-biometric path

Staff manual override/review already records a reason and actor. A user-facing equivalent path remains to be implemented before requiring biometric attendance.

## Deferred decisions requiring evidence

1. Device-to-backend identity method (mTLS, signed assertions, or another reviewed mechanism).
2. Edge hardware and inference provider based on measured complete-pipeline latency, memory, maintainability, and cost.
3. Passive PAD model, sensor type, evaluation protocol, and thresholds.
4. Offline sync protocol, roster freshness policy, clock-skew handling, and event signature scheme.
5. Managed encryption/KMS provider, key version format, rotation, and restore strategy.
6. WebSocket/SSE transport if measured polling load or latency warrants it.
7. Proximity verification hardware and platform support; NFC/manual fallback remains necessary.

## Non-goals

- No emotion recognition, individual gaze/attention scoring, or continuous behavior profiling.
- No fabricated accuracy, FPS, RTT, liveness, security-certification, or deployment-health claims.
- No global unrestricted face search for a room scanner; target matching must use an authorized roster.
