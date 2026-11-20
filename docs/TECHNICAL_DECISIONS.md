# AttendX — Technical Decisions (ADRs)

These are **proposed** decisions based on the audit. They require your approval before implementation. Each entry records context, decision, and consequences.

---

## ADR-001 — Keep React 18 + MUI + CRA/Craco (defer TypeScript/Vite/Tailwind)

- **Context:** The master prompt suggests TypeScript + Vite + Tailwind "where appropriate". The repo is a working JS/CRA/MUI app with an established theme, 18 components, tests, and build/CI pipeline; Phase 6 already hardened it (0 warnings, smaller bundle).
- **Decision:** Do **not** rewrite the frontend stack. Extend it with a design system, tokens, dark theme, and new screens. Introduce TypeScript/Vite/Tailwind only in a separate, explicitly-approved migration.
- **Consequences:** Preserves UI, navigation, and CI; avoids a high-risk rewrite. "TypeScript checks" in the acceptance criteria would be N/A unless a migration is approved.

## ADR-002 — Keep InsightFace / ArcFace as the recognition engine

- **Context:** InsightFace `buffalo_l` (SCRFD detector + ArcFace `w600k_r50`, 512-d normalized embeddings) is already implemented, DB-backed, CPU-capable, calibrated via a benchmark script, and covered by tests.
- **Decision:** Retain it. Do not add AdaFace or a second embedding model unless a measured evaluation on a representative dataset shows a concrete benefit.
- **Consequences:** No accuracy claims without evaluation; thresholds stay configurable and documented (`FACE_MATCH_THRESHOLD` etc.), with model version recorded per verification event (new phase 5 work).

## ADR-003 — Liveness: keep active head-turn challenge; treat passive PAD as research

- **Context:** `services/liveness.py` documents that a passive single-image anti-spoofing candidate classified **all 64 real enrollment photos as spoof**, which would lock out every user. The active, server-issued head-turn challenge is deterministic and blocks photos/stills/non-matching replays.
- **Decision:** Keep the active challenge as the shipped defence. Do not integrate MiniFASNet/Silent-FAS until a model is licensed, evaluated on printed-photo/phone-display/video-replay attacks **and** real users, with results committed. Unknown-face/manual fallback remains.
- **Consequences:** We will **not** claim "AI anti-spoofing detects all attacks" or ISO certification. `docs/AI_MODELS.md` will state the exact evaluated scope and the failed PAD evaluation.

## ADR-004 — Multi-face: additive pipeline, single-face flow preserved

- **Context:** Current code picks the largest face (`_largest_face`) and locks identity to the authenticated user.
- **Decision:** Add a separate multi-face detection/tracking service (InsightFace detector + ByteTrack or a lightweight IoU/centroid tracker) with stable temporary IDs, quality-based frame selection, and embeddings computed only on selected frames. Keep the existing single-face enrollment/mark endpoints working; new multi-face live-monitor endpoints are additive.
- **Consequences:** ByteTrack is explicitly a tracker, not a recognizer — identity still comes from ArcFace. No embeddings per frame (cost control). CPU-compatible operation preserved. Live multi-face accuracy must be validated on real hardware by the user.

## ADR-005 — Three roles by extending `users.role`, not by forking identity tables

- **Context:** `users.role` is a string (`admin`/`user`). The prompt requires admin/teacher/student.
- **Decision:** Extend the role values to `admin`/`teacher`/`student` and add optional academic profile tables (`students`, `teachers`) keyed to `users`. Existing `user` rows are migrated to `student` (or kept backward-compatible via an alias) with an additive migration.
- **Consequences:** Existing users and data preserved. Backend permission checks via `deps.py` must be extended for every new endpoint. Requires a data-migration decision on the meaning of legacy `user` accounts (confirm with user).

## ADR-006 — Attendance sessions are additive; keep per-day uniqueness

- **Context:** Attendance is one row per user per day (DB unique constraint), with shift-aware punctuality. The prompt requires sessions with start/stop and one record per student per session.
- **Decision:** Add `attendance_sessions` and session-linked records, but keep the existing daily table and constraint for backward compatibility until session-based flows are fully adopted. Session decisions flow through a unified decision engine with outcomes VERIFIED / REVIEW_REQUIRED / REJECTED / DUPLICATE / MANUAL_OVERRIDE.
- **Consequences:** Some duplication of concepts during transition; no existing data lost. Unique constraint added at DB level for (session_id, student_id).

## ADR-007 — Offline sync via new SQLite queue + idempotent batch API

- **Context:** No offline support exists. Browser-local persistence must survive restarts and duplicate submissions.
- **Decision:** New client-side SQLite event queue with UUID event IDs, exponential backoff, sync status, and a new idempotent `POST /api/v1/events/batch` endpoint that records sync events and never silently discards data.
- **Consequences:** New tests for offline/reconnect/restart/duplicate/partial-failure scenarios. Browser storage choice (IndexedDB vs SQLite WASM) to be decided at implementation time based on build compatibility.

## ADR-008 — No pgvector

- **Context:** 512-d embeddings live in Postgres; prompt suggests pgvector "only when vector search is required".
- **Decision:** Do not add pgvector. Current matching loads gallery vectors into a numpy cache and computes cosine similarity + k-NN; this is adequate at expected scale and keeps deployment simple.
- **Consequences:** Revisit only if gallery size makes in-memory matching impractical (measure first).

## ADR-009 — Privacy: additive consent, separation, encryption; no raw-image exposure

- **Context:** Embeddings/images currently stored raw in DB; no consent/retention tables; APIs never expose embeddings (good).
- **Decision:** Add `consent_records`, retention policy enforcement, a separate `biometric_templates` table decoupled from PII, and encryption of sensitive fields at rest. Keep embeddings out of all API responses. Provide a non-biometric check-in fallback and template revocation (extend existing face-delete endpoints).
- **Consequences:** New crypto/key-management surface (keys via env/secret manager, never in code). Indian DPDP review required before institutional deployment. This phase must be validated carefully to avoid breaking existing enrollment data.

## ADR-010 — API v1 via additive prefixes

- **Context:** Routes are currently unversioned (`/auth/login`, `/attendance`).
- **Decision:** Mount new endpoints under `/api/v1/*` while keeping legacy paths working (additive aliases or a second router registration). No breaking API changes.
- **Consequences:** Some route duplication; documented in `docs/API_DOCUMENTATION.md`.

## ADR-011 — Documentation set added without removing existing docs

- **Context:** Only `README.md` and `backend/README.md` exist.
- **Decision:** Add the requested `docs/*` files, each describing **actual implemented** functionality and clearly separating done vs planned. Keep README as the entry point.
- **Consequences:** Docs must be updated in the same phase as the code they describe.

---

## Open questions requiring user approval before implementation

1. Confirm the target codebase: this repository (React/MUI + FastAPI) or a separate Streamlit repository?
2. Approve ADR-001 (defer frontend stack migration) and ADR-003 (no passive PAD claim until evaluated).
3. Approve the role-mapping decision for legacy `user` accounts (ADR-005).
4. Approve session model with backward-compatible daily uniqueness (ADR-006).
5. Approve the phase reordering in `IMPLEMENTATION_ROADMAP.md` (backend pipeline before final frontend consolidation).
6. Confirm that Phase 6 passive anti-spoofing may be **scoped down** to "evaluated, not deployed" if no suitable licensed model/dataset exists — to avoid promising a capability we cannot validate.
