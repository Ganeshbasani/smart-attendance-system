# Implementation Roadmap

This plan extends the current application incrementally. Each stage must remain runnable, preserve existing daily attendance and scheduling data, include tests, update [FEATURE_STATUS.md](FEATURE_STATUS.md), and report measured results separately from targets.

## Current progress

| Stage | State | Notes |
|---|---|---|
| 0. Repository audit | Complete for current repository state | Audit and architecture docs refreshed; security and feature matrices added |
| Session authorization | Implemented, tests added but not executable locally | Anonymous submissions blocked; student self/class scope; staff session ownership; event feed restricted |
| 1. CV foundations | Partial | Added detector-only SCRFD path, quality scoring, ArcFace alignment/normalization, tests; local dependency environment lacks OpenCV |
| 2. Multi-face tracking | Partial, standalone service | Two-stage Kalman/IoU ByteTrack-style association and stable ephemeral IDs; no camera/API/session integration or physical validation |
| 3. PAD and synchronized RGB-IR | Not started | Keep active challenge; evaluate licensed candidates and hardware before deployment |
| 4. Batch event sync and offline queue | Not started | Define authenticated device/event protocol first |
| 5. Consent, encryption, retention, fallback | Not started | High priority before broader biometric deployment |
| 6. Device registry, heartbeat, operations | Not started | No device metrics should be displayed until actual reporting exists |
| 7. Dashboard integration and real-time push | Partial | Polling session monitor exists; connect scanner and add push only when justified |
| 8. Evaluation, CI, deployment hardening | Partial | Existing CI remains; current tests could not execute in this environment |

## Stage 1 — Establish a trusted scanner contract

1. Define a scanner identity and authentication mechanism; prohibit browsers from asserting liveness, model version, or match score as trusted facts.
2. Decide whether scanning runs on a managed edge device or on the API host. If edge-based, issue revocable device credentials and scope each device to rooms/classes.
3. Define a versioned request schema for pseudonymous result, active session, quality, liveness provenance, model version, capture time, and idempotency key.
4. Preserve raw frames within the chosen scanner boundary and set explicit upload/retention rules.

**Gate:** threat model and API contract reviewed; unauthorized devices/users cannot submit or view data outside their scope.

## Stage 2 — Integrate and evaluate multi-face scanning

1. Connect the isolated detector/tracker to a managed camera loop with bounded queues and explicit frame-drop behavior.
2. Add quality metrics for pose, illumination, minimum face size, and blur; reject unknown or low-quality matches rather than force an identity.
3. Restrict matching to the active session's authorized roster. Return an uncertain/review outcome when thresholds or data quality do not support a confident decision.
4. Integrate track outputs with session decisions using device-authenticated submissions, without exposing embeddings to the browser.
5. Run consented, separated validation and held-out test sets on the actual camera/hardware. Record false match/non-match and review rates.

**Gate:** observed latency/FPS, held-out identity evaluation, camera-placement guidance, failure handling, and rollback path. Hardware performance targets are not assumed.

## Stage 3 — Liveness and attack evaluation

1. Keep server-issued active head-turn challenge as the current liveness method.
2. Assess passive PAD model licensing, provenance, runtime compatibility, genuine-user behavior, and print/screen/video attack coverage.
3. Add RGB-IR only after selecting hardware and validating synchronized capture. An RGB-only camera must never emit an infrared verification claim.
4. Report APCER/BPCER/ACER only from a documented evaluation set; do not claim ISO certification without independent certification/evaluation.

**Gate:** approved threat model, reproducible test procedure, versioned model, and measured error rates on target sensors.

## Stage 4 — Reliable edge event synchronization

1. Add edge-device enrollment, mTLS-ready credentials, key revocation, heartbeat, and room scope.
2. Implement `/api/v1/events/batch` with schema validation, signed or authenticated event provenance, UTC timestamps, idempotency keys, row-level result reporting, and transaction-safe writes.
3. Add a SQLite WAL queue with pending/sent/retry state, bounded backoff, restart recovery, and operator visibility.
4. Validate clock skew and stale roster policy; avoid trusting a device-supplied timestamp without bounds and provenance.
5. Simulate 1,000 events during a 30-minute disconnect, repeated submissions, partial failures, process restart, and reconnect. Report actual zero-loss/duplicate results only if observed.

**Gate:** integration tests on the actual backend database; deterministic idempotency and recoverable per-event failures.

## Stage 5 — Privacy and data lifecycle

1. Add consent records with purpose, notice version, consent/withdrawal timestamps, and actor/source.
2. Separate biometric templates from public profile identifiers; generate pseudonymous references and enforce service-level access.
3. Implement envelope encryption with a supported key provider, key rotation, revocation, and backup implications. Do not expect ordinary pgvector distance search to work on ciphertext.
4. Define retention schedules and auditable deletion for templates, enrollment images, events, logs, and backups.
5. Add an equivalent non-biometric check-in path plus user access/deletion workflows.

**Gate:** threat-model review, migration/rollback plan, key-recovery test, deletion verification, and privacy-owner review for the deployment jurisdiction.

## Stage 6 — Device and administrative operations

1. Add device table, scoped room/class assignments, heartbeat, software/model version, health timestamps, and pending-sync counts.
2. Collect only metrics devices actually report; mark stale values and offline state honestly.
3. Build dashboard cards and alerts over the real APIs. Do not seed production cards with fabricated operational metrics.
4. Add pagination, filtering, exports, and audit history as actual endpoints/actions.
5. Add WebSocket or server-sent event delivery only if API polling is measured to be inadequate.

## Stage 7 — Evaluation, CI, and production readiness

- Unit tests: detection validation, alignment and normalization, similarity, tracker lifecycle, quality scoring, decision provenance, authorization, event signing, encryption, deletion.
- Integration tests: camera/scanner adapter, recognition to attendance, PostgreSQL migrations, idempotent batch sync, device heartbeat, overrides, dashboard APIs.
- Performance report: FPS, detection/tracking/recognition/end-to-end latency, resource use, database latency, queue growth, and active-session cost on named hardware.
- Evaluation: separate consented train/tune and held-out data. Report FMR/FNMR/FPIR/FNIR/TAR and PAD APCER/BPCER/ACER only where the protocol supports them.
- Deployment: dependency/model version pinning, vulnerability scanning, health checks, backups, restore drills, secure secrets, and documented rollback.

## Priority order

1. Complete and execute the authorization regression tests.
2. Establish the trusted scanner/device contract.
3. Complete camera integration and evaluate multi-face recognition on target hardware.
4. Deliver consent, encryption, retention, and non-biometric fallback before broader biometric use.
5. Implement batch/offline sync and device health reporting.
6. Evaluate PAD/proximity and add only supported hardware integrations.
7. Complete dashboard, load, performance, deployment, and recovery validation.
