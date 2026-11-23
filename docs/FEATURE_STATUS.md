# Feature Status

Maintained status of product capabilities. “Implemented” means code exists in this repository; it does not imply independent validation, production deployment, or measured accuracy.

| Capability | Status | Current evidence | Remaining work |
|---|---|---|---|
| Authentication and account management | Implemented | JWT auth, password hashing, active-account checks, profile/password routes | Security review of token storage and deployment policies |
| Admin/teacher/student roles | Implemented | Role dependencies, profiles, dashboards | Add broader cross-role tests and least-privilege review |
| Academic CRUD and class enrollment | Implemented | Versioned academic routes and admin UI | Pagination/scale review and integration testing |
| Organization sectors and class groups | Implemented | Admin can configure school, college, office, or other; class groups support level and optional section labels | Multi-organization tenancy and sector-specific workflows remain future work |
| Manual present/absent attendance | Implemented, verification pending | Teacher/admin class roll call, complete-roster finalization, audited edits, day/month/year summaries and per-student percentages | Backend integration tests and deployment migration validation |
| Roster document import | Partial | Review-before-import for CSV, DOCX tables, and text-based PDFs; up to 500 rows | Scanned PDFs need OCR; new imported accounts are inactive pending admin setup |
| Daily attendance, shifts, leave, corrections | Implemented | Legacy attendance/scheduling routes and models | Maintain compatibility while session flow grows |
| Attendance sessions and decisions | Implemented | Lifecycle, policy engine, unique session record, review/manual override | Bind decisions to trusted scanner provenance |
| Session authorization | Hardened, verification pending | Score-based submissions are staff-only pending trusted scanner auth; scoped reads, staff ownership, class enrollment checks, and view-only camera UI | Run CI; add cross-class/PostgreSQL integration tests |
| Single-face ArcFace recognition | Implemented | InsightFace recognition, embeddings, cosine/k-NN matcher | Representative held-out FMR/FNMR evaluation and threshold report |
| Capture quality checks | Partial | Size, blur, detection confidence, brightness; new scanner quality heuristic | Pose/occlusion and model-specific evaluation/calibration |
| Multi-face SCRFD detection | Partial, service only | Detector-only backend returns boxes/landmarks | Wire to managed camera pipeline, roster-limited matching, operator UI |
| Multi-face tracking | Partial, service only | Kalman prediction, two-pass confidence association, ephemeral IDs | Physical occlusion/crowd validation; scanner session/device integration |
| Selective recognition | Partial, service only | Embedding can be computed on confirmed track quality improvement | Wire to gallery matching and define deduplication/cooldown policy |
| Active liveness | Implemented for current kiosk flow | Server-issued head-turn challenge | Shared challenge state for multi-worker deployment; evaluation limits documented |
| Passive PAD / RGB-IR | Not implemented | Previous candidate not suitable; no IR camera integration | Licensed model and sensor-specific attack/genuine-user evaluation |
| Offline edge processing | Not implemented | No local roster or durable queue | Device identity, signed events, WAL queue, retry, reconciliation |
| Batch event API | Not implemented | No `/api/v1/events/batch` | Idempotent validation and transactional sync implementation |
| pgvector/HNSW | Not implemented | In-process NumPy cosine gallery cache | Reconsider after measured scale/selective-filter bottlenecks |
| Biometric consent and retention | Incomplete | No consent/retention lifecycle | Consent, withdrawal, retention jobs, user deletion and audit |
| Application-layer template encryption | Not implemented | DB stores vectors/images without envelope encryption | Managed KMS-compatible envelope encryption and tested key rotation |
| Non-biometric self-service fallback | Partial | Staff can manually override with reason | User-facing badge/code/manual fallback with equivalent policy |
| Proximity verification | Not implemented | No RTT/NFC evidence or API | Optional device-specific module; simulator clearly labeled; physical validation |
| Device inventory/health | Not implemented | No device model/heartbeat | Scoped device registration, real heartbeat and metrics API |
| Live attendance UI | Partial | Session monitor polls backend, preview is view-only | Integrate trusted scanner results; push transport only if warranted |
| Analytics and CSV | Implemented | Daily/weekly analytics and CSV export | Session/course/room analytics; PDF reports if needed |
| WebSocket feed | Not implemented | Polling currently used | Add only after measured need and auth design |
| Docker and CI | Implemented in repository | Compose, Dockerfiles, CI workflow | Current local runtime not available for verification; confirm CI and restore drills |
| Performance/biometric evaluation | Not measured | No valid report generated in this pass | Reproducible dataset protocol and named hardware benchmarks |

## Status vocabulary

- **Implemented:** feature has a functional code path in this repository.
- **Partial:** some components work, but an integration, required behavior, or validation is missing.
- **Not implemented:** no production code path exists.
- **Verification pending:** code/tests were added, but the required execution environment was unavailable.

Do not promote partial, simulated, or unmeasured features to “implemented” in product copy without completing the listed work.
