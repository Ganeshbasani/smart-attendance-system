# Security Notes

## Threat model

AttendX is designed to reduce common classroom attendance abuse without treating automated signals as proof of misconduct.

### Risks addressed

- weak/plaintext password storage
- brute-force login attempts
- duplicate attendance
- copied/expired QR codes
- one browser identity used across multiple students
- unusually fast check-in bursts
- untraceable corrections
- false "synced" status after a connectivity interruption

### Controls

- PBKDF2-SHA256 password hashing with unique salt
- failed-login throttling
- parameterized SQL queries
- foreign keys and uniqueness constraints
- HMAC-signed, short-lived verification tokens
- explicit device registration
- attempt logging
- anomaly evidence
- human review for suspicious sessions
- audit trail
- idempotent offline queue synchronization
- no mandatory face recognition or continuous location tracking

## Known limitations

A browser/device token is not a hardware attestation mechanism. It is an additional layer, not a guarantee against account sharing.

The Streamlit version does not ship a true offline PWA. The offline requirement is implemented through queue export/import and idempotent reconciliation. A true disconnected mobile/browser capture experience should be implemented as a dedicated client if the institution requires it.

Document uploads are stored on the local filesystem in this portfolio build. Production deployments should use encrypted object storage and a formal retention policy.

Production deployments should use SSO/OIDC, a managed database, TLS, centralized secrets, and hardened infrastructure.
