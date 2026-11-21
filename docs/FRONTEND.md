# AttendX Frontend (Phase 3)

**Status:** implemented and verified. This document describes only what exists now; planned work is listed at the end.

## Stack (unchanged, per ADR-001)

React 18 (JavaScript) · MUI 5 · CRA + Craco · React Router · axios · Recharts · framer-motion · MediaPipe Tasks Vision · react-webcam. No TypeScript/Vite/Tailwind rewrite was performed.

## Design system

- `src/theme/ThemeContext.js` — `createAppTheme(mode)` builds the AttendX MUI theme (navy `#212E46`, orange `#f97316` accent, Inter typography, 12px radius, consistent overrides). `ThemeModeProvider` persists the selected mode to `localStorage` (`attendx-theme-mode`) and exposes `useThemeMode()` with `toggleMode`/`setMode`.
- `index.js` now mounts `ThemeModeProvider` (which owns `ThemeProvider` + `CssBaseline`) instead of a static light theme.
- `src/components/ui/index.js` — reusable `PageHeader`, `StatCard`, `StatusChip`, `LoadingState`, `EmptyState`, `ErrorBanner`, `ConfirmDialog`, and `DataTable`. Every new screen uses these, so loading/empty/error states are consistent.
- Navbar: theme toggle (desktop icon button + mobile menu item), role-aware labels, dark-mode-aware surface colors, and links to the new screens.

## Screens added

| Route | Screen | Real behaviour |
| --- | --- | --- |
| `/admin/academic` | `AcademicManagement` | Admin-only CRUD over departments, academic sessions, courses, teachers, students, and classes via `/api/v1/*`; enroll/unenroll students in classes; confirm dialogs, snackbars, pagination-friendly tables, 409/404 error surfacing. Create/edit dialogs omit passwords on edits (the backend's `*Update` schemas are partial). |
| `/teacher` | `TeacherDashboard` | Staff-scoped class/student counts from `/api/v1/classes` and `/api/v1/students`; "Mark attendance" navigates to the working kiosk flow. |
| `/student` | `StudentDashboard` | Attendance %, present/absent counts from `/user/attendance/stats`, recent records from `/user/attendance`, pending leave count; functional leave-request dialog via `/user/leave-requests`; history and correction links. |
| `/settings` | `SettingsPage` | Theme mode switch, account summary, sign out, and real password change via `/user/change-password`. |

`/dashboard` now routes by role: admin → AdminDashboard, teacher → TeacherDashboard, student (including legacy `user`) → StudentDashboard.

## API layer additions (`src/services/api.js`)

- `authAPI.me()` → `GET /auth/me`.
- `academicAPI` → generic `list/create/update/remove` over versioned resources plus `listEnrollments/enroll/unenroll`.

All calls carry the existing JWT interceptor; no auth behaviour changed.

## Tests

- `src/components/AcademicManagement.test.js` (2 tests): renders all six resource tabs, opens the create dialog, and verifies the v1 list call.
- `src/theme/ThemeContext.test.js` (2 tests): both themes build with the AttendX palette/typography.
- Existing App (3) + ErrorBoundary (2) tests still pass: **9 frontend tests total**.

## Known limitations / planned

1. **No live multi-face monitor yet.** Session start/stop, tracked IDs, spoof alerts, and review queues require the Phase 7 backend decision engine and session API. No decorative controls were added.
2. **Legacy screens** (AdminDashboard, EmployeeDashboard, Home, etc.) still use hardcoded light colours; dark mode fully applies to new/theme-aware surfaces only.
3. **TypeScript/Vite/Tailwind migration** deferred per ADR-001.
4. `StudentDashboard` "Request a correction" navigates to the existing attendance-history screen, where correction requests are created; it is not a separate dialog yet.
5. Teacher analytics remains admin-only in the backend (`/analytics/*` uses the admin guard), so the teacher portal shows only class/student data it can actually access.
