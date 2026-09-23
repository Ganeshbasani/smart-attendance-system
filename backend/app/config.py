from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AttendX"
    api_prefix: str = "/api"
    secret_key: str = "change-this-attendx-development-secret-key-2026"
    access_token_minutes: int = 60
    database_url: str = "sqlite:///./data/attendx.db"
    frontend_origin: str = "http://localhost:5173"
    qr_ttl_seconds: int = 20
    uploads_dir: str = "./data/uploads"
    semester_end: str = "2027-04-30"
    attendance_threshold: float = 75.0
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
