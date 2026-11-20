# AttendX — Implementation Roadmap

**Status:** planning only. No implementation work has started under this master prompt. Existing committed work (hardening Phases 1–7) is treated as the baseline.

## 1. Guiding principles

1. Extend, do not rewrite. No feature removal, no destructive migration of existing user data.
2. Every phase: inspect → explain → list affected files → implement → backend tests → frontend tests + build → regression check → API-compatibility check → document → report.
3. No invented model accuracy, no untested claims, no hardcoded secrets, no decorative buttons.
4. Each phase ends with a runnable, tested increment and an 11-section report.
5. Commit only on explicit user approval ("go ahead"). Never force-push or delete branches.

## 2. Phase map (master prompt phases ↔ repository state)

| Phase | Goal | State at audit | Complexity | Key new artifacts |
|---|---|---|---|---|
| 0 | Repository audit | **Done by this audit** | — | `docs/PROJECT_AUDIT.md`, `CURRENT_ARCHITECTURE.md`, `TECHNICAL_DECISIONS.md`, this file |
| 1 | Architecture / technical design | Partially covered by audit docs; needs approval on open decisions | Low | ADR sign-off |
| 2 | Backend & database foundation | **Mostly present** (FastAPI, SQLAlchemy, Alembic, 10 tables, JWT, RBAC). Needs: 3 roles, academic-domain tables, v1 API prefix | Medium | migrations, `academic` models, `deps` role checks |
| 3 | Professional frontend | React/MUI present; needs role portals, live monitor, design system, light/dark themes | High | new components, theme tokens, screens |
| 4 | Multi-face detection & tracking | Single-face InsightFace present; add multi-face wrapper + tracker + stable IDs | High | CV pipeline module, tracker, frame selection |
| 5 | Face quality & identity verification | Quality + ArcFace present; extend quality dimensions and decision instrumentation | Medium | quality scorer, verification event records |
| 6 | Anti-spoofing integration | Active head-turn challenge present; passive PAD **not usable** (failed evaluation) — needs model re-evaluation with a real dataset | High / research | PAD adapter, evaluation harness, documented results |
| 7 | Smart attendance decision engine | Logic scattered in routers; add unified engine + outcome vocabulary + session enforcement | Medium | decision engine service, session models |
| 8 | Offline synchronization | Missing | Medium-high | SQLite event queue, idempotent batch endpoint, backoff, tests |
| 9 | Analytics & anomaly detection | Strong rule-based analytics present; add anomaly records/review queue and role-scoped views | Medium | anomaly model, review endpoints, dashboards |
| 10 | Privacy & security | Auth/audit present; add consent, retention, template separation, encryption-at-rest, non-biometric fallback | High | new tables, crypto layer, fallback flow |
| 11 | Integration & testing | 183 backend + 5 frontend tests; add integration/E2E (Playwright), Ruff, perf instrumentation | High | E2E suite, CI extensions |
| 12 | Documentation & deployment | README + backend README present; add full `docs/` set, verify deployment instructions | Medium | remaining docs, verified deploy notes |

## 3. Recommended sequencing (dependencies first)

```
Phase 1 decisions (roles, framework scope, PAD strategy)
   ↓
Phase 2 foundation (roles + academic schema + v1 API aliases)
   ↓
Phase 7 decision engine + sessions   ← must precede multi-face/live monitor
   ↓
Phase 4 multi-face + tracking  →  Phase 5 quality extension  →  Phase 6 PAD re-evaluation
   ↓
Phase 8 offline sync  →  Phase 9 analytics/anomalies  →  Phase 10 privacy/security
   ↓
Phase 11 integration tests  →  Phase 12 documentation/deployment
   ↓
Phase 3 frontend portals & live monitoring (incremental across all of the above; final consolidation here)
```

The prompt numbers phases 3 before 4, but frontend live monitoring depends on the backend session/decision/Multi-face APIs. Frontend work should therefore proceed incrementally, with a consolidation pass after the backend pipeline exists. **Approval required for this reordering.**

## 4. Hardware compatibility assessment

- **Available:** local Windows machine, CPU-only Python venv (`onnxruntime` CPU provider, `insightface` buffalo_l already runs in Docker and locally); Docker Desktop available (had to be started manually). No GPU detected/configured (`FACE_USE_GPU=false`).
- **CPU viability:** InsightFace SCRFD + ArcFace at `det_size=(640,640)` runs on CPU today (verified via container `/ready` smoke and existing tests). Adding ByteTrack is CPU-friendly (pure numpy/OpenCV). MiniFASNet inference is lightweight on CPU, but a usable model + representative dataset is not present.
- **Camera:** browser camera via `react-webcam` + MediaPipe; actual multi-face live testing requires a physical webcam, which cannot be verified in this environment — must be validated by the user on supported hardware and reported honestly.
- **No purchases:** no paid services/hardware will be used without approval.

## 5. Open-source dependency recommendations

**Reuse (already present):** insightface, onnxruntime, opencv-python, numpy, scipy, SQLAlchemy, Alembic, psycopg2-binary, FastAPI, Pydantic, slowapi, passlib, python-jose, pytest, React Testing Library, MediaPipe Tasks Vision, react-webcam, Recharts.

**Add only when the corresponding phase starts (with justification):**
- `bytetrack` (or implement a small IoU/centroid tracker first) — Phase 4.
- `ruff` — Phase 11 (lint).
- `@playwright/test` — Phase 11 (E2E).
- Passive PAD model weights (MiniFASNet / Silent-FAS) — Phase 6, **only after** license + evaluation review; must not be claimed effective without measured results.
- **Do not add** pgvector (512-d numpy cosine is sufficient at current scale), and **do not migrate** CRA→Vite/JS→TS/MUI→Tailwind unless explicitly approved (see Technical Decisions ADR-001).

## 6. Target database design (additive to existing 10 tables)

New tables: `roles`/role enum extension on `users`, `students`, `teachers`, `departments`, `courses`, `classes`, `class_enrollments`, `attendance_sessions`, `verification_events`, `offline_sync_events`, `consent_records`, `biometric_templates` (split from PII), `anomaly_flags`.
Cross-cutting: UUID columns where new tables are introduced, FK constraints, unique constraints (one record per student per session), indexes on date/user/session, created_at/updated_at on new tables, transaction-safe attendance writes. Existing data is preserved via additive Alembic migrations; the daily-unique attendance constraint remains for backward compatibility until sessions are fully adopted.

## 7. UI/UX design plan

Keep the existing design language (Inter, navy `#212E46`, warm neutral backgrounds, orange accents, MUI component styling, framer-motion animations). Introduce a formal design system (tokens for color/spacing/radius/shadow, shared `Card`/`StatCard`/`DataTable`/`EmptyState`/`StatusChip` components), light/dark theme toggle, responsive breakpoints, and consistent loading/error/empty states. New screens: student/teacher/admin portals, live attendance monitor (camera preview, face boxes, tracked IDs, verified/review/spoof queues, counters, manual verification, session controls), class/session management, audit & security, settings. Every control must be wired to a real API action.

## 8. Testing strategy

- **Backend:** extend Pytest per module (auth/RBAC, academic CRUD, sessions, decision outcomes, multi-face unit tests on recorded frames, quality scorer, liveness, batch idempotency, analytics, anomaly rules). Never fabricate results; record failures.
- **Frontend:** keep React Testing Library tests; add Playwright for critical flows (login, enrollment, mark, correction, dashboards) and responsive checks once the role portals exist.
- **Quality:** Ruff for Python; `CI=true npm run build` (ESLint gate) for frontend; TypeScript checks only if the frontend is migrated to TS.
- **Integration gates:** after each module, run full backend + frontend suites, build, and a live smoke (backend on 8000, frontend on 3000) where possible.
- **Performance:** instrument detection/tracking/recognition/liveness/total latency, FPS, CPU/RAM, API and DB latency during Phase 11; publish real numbers in `docs/PERFORMANCE_REPORT.md`. No invented figures.

## 9. Estimated implementation complexity (relative, not calendar time)

| Workstream | Relative size |
|---|---|
| Academic schema + 3 roles + v1 API | M |
| Decision engine + sessions | M |
| Multi-face detection + tracking + CPU frame selection | L |
| Quality expansion + verification events | M |
| Passive PAD with real evaluation | XL / research-heavy |
| Offline sync queue + retries + tests | M–L |
| Analytics/anomaly extension | M |
| Privacy/security (consent, encryption, fallback) | L |
| Frontend portals + live monitor + design system | XL |
| Testing/performance/docs/deployment | L |

Total: a large, multi-phase program. The passive PAD and live-camera validation are the highest-uncertainty items and should be explicitly scoped/approved before being promised.

## 10. Validation gates (each phase)

1. All existing tests still pass (183 backend / 5 frontend baseline, growing).
2. New tests written alongside new code and passing.
3. CI build compiles with zero warnings.
4. Alembic chain has a single head; migration round-trip verified.
5. No API/UI regression; no fabricated results in reports.
6. Docs updated in the same phase; 11-section phase report delivered.
