import hashlib
import hmac
import secrets
from datetime import datetime, timezone, timedelta

from config import SESSION_MINUTES
from db import query_one, execute, utc_now_iso


def utc_now():
    return datetime.now(timezone.utc)


def hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240_000)
    return f"pbkdf2_sha256$240000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(expected.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def new_session():
    token = secrets.token_urlsafe(24)
    return {
        "token": token,
        "created_at": utc_now(),
        "expires_at": utc_now() + timedelta(minutes=SESSION_MINUTES),
    }


def session_valid(session):
    return bool(session and session.get("expires_at") and session["expires_at"] > utc_now())


def login_allowed(username: str, max_failures: int = 5, window_minutes: int = 10) -> bool:
    row = query_one(
        """SELECT COUNT(*) AS failures
           FROM login_attempts
           WHERE username=? AND success=0
             AND datetime(attempted_at) >= datetime('now', ?)""",
        (username.strip(), f"-{window_minutes} minutes"),
    )
    return int(row["failures"] or 0) < max_failures


def record_login_attempt(username: str, success: bool):
    execute(
        "INSERT INTO login_attempts(username,attempted_at,success) VALUES (?,?,?)",
        (username.strip(), utc_now_iso(), 1 if success else 0),
    )
