# AttendX — Database Schema

Schema is managed by Alembic. Current head: `e7f8a9b0c1d2` (Phase 2).
Migration chain:

```
2143901ce032 (initial)
  -> be4c008c9294 (face embeddings/images)
  -> 7c9e1f4b2a81 (daily attendance unique + date index)
  -> f4a1c2b3d4e5 (audit logs)
  -> a5b6c7d8e9f0 (scheduling domain)
  -> d4e5f6a7b8c9 (notifications)
  -> e7f8a9b0c1d2 (academic domain — Phase 2)
```

## Existing tables (preserved unchanged in Phase 2)

| Table | Purpose | Notable constraints |
| --- | --- | --- |
| `users` | Identity, hashed password, `role`, shift, face flag | unique email + unique_id |
| `attendance` | Daily attendance record | **unique (user_id, date)** |
| `face_embeddings` | One packed 512-d float32 matrix per user | unique user_id, `count`, `dim`, `model` |
| `face_images` | Enrollment JPEG bytes | FK user_id, `position`, `quality_score` |
| `audit_logs` | Action, actor, entity, details | indexed |
| `notifications` | User-scoped notifications | FK user_id, is_read |
| `shifts`, `holidays` | Scheduling context | — |
| `leave_requests`, `attendance_correction_requests` | Approval workflows with reasons | FK user_id |

## Tables added in Phase 2 (all additive)

| Table | Columns | Constraints |
| --- | --- | --- |
| `departments` | id, name, code, created_at, updated_at | unique name, unique code |
| `academic_sessions` | id, name, start_date, end_date, is_active, timestamps | unique name; `end_date >= start_date` validated in API |
| `courses` | id, name, code, department_id, credits, timestamps | unique code; FK department (SET NULL) |
| `teachers` | id, user_id, employee_id, department_id, timestamps | unique user_id, unique employee_id; FKs |
| `students` | id, user_id, roll_number, department_id, academic_session_id, timestamps | unique user_id, unique roll_number; FKs |
| `classes` | id, name, code, course_id, teacher_id, academic_session_id, timestamps | unique code; FKs to courses/teachers/sessions |
| `class_enrollments` | id, class_section_id, student_id, created_at | **unique (class_section_id, student_id)**; FKs with CASCADE |

## Role model

- `users.role` is a string: `admin`, `teacher`, `student`.
- Migration `e7f8a9b0c1d2` converts legacy `role='user'` rows to `'student'`.
- `require_student` accepts both `student` and legacy `user`; `require_teacher`
  and `require_staff` enforce the new roles.
- New registrations default to `student`; `ADMIN_EMAIL` gets `admin`.

## Design notes

- No existing column was altered or dropped; existing user data, attendance,
  and biometric records are untouched by the Phase 2 migration.
- All new tables have integer PKs with indexes, created/updated timestamps,
  and foreign keys with explicit `ondelete` behaviour.
- Attendance remains tied to `users` (not `students`) for backward
  compatibility. Session-linked attendance is planned for Phase 7 of the
  AttendX program and will be additive.
- The API layer enforces uniqueness with friendly 409 responses; the database
  constraints remain the final guarantee (global IntegrityError handler → 409).
