# AttendX Product Audit & Scope

## Keep

Attendance Runway, explainable risk, prediction, early intervention, signed dynamic QR, device verification, session anomaly detection, notifications, correction/condonation, audit trail, role-specific views, offline reconciliation, Docker/CI/testing.

## Remove

Generic AI chatbot, decorative charts, fake ML, arbitrary dashboard counters, face recognition as a default control, continuous GPS, unnecessary microservices, excessive animation and duplicated screens.

## Production gaps for a real institution

1. Managed object storage + malware scanning for documents.
2. SSO/OIDC and institutional identity integration.
3. PostgreSQL backups, migrations and connection pooling as deployment standards.
4. Message/email/SMS provider for outbound notifications.
5. Stronger device enrollment/recovery policies for managed campus devices.
6. Integration adapters for SIS/LMS/timetable sources.

These are deliberate boundary decisions rather than reasons to inflate the application with unrelated technologies.
