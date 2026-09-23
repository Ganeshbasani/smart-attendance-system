import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("ATTENDX_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "attendx.db"
DOCUMENT_DIR = DATA_DIR / "documents"
DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.getenv("ATTENDX_SECRET_KEY") or "dev-only-change-me-" + secrets.token_hex(16)
SESSION_MINUTES = int(os.getenv("ATTENDX_SESSION_MINUTES", "30"))
PRODUCT_NAME = "AttendX"
PRODUCT_TAGLINE = "Attendance Intelligence & Early Intervention"

TIMEZONE_NAME = os.getenv("ATTENDX_TIMEZONE", "Asia/Kolkata")
