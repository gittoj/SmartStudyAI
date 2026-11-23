from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

# libpq options that hosts such as Neon put in their URLs but asyncpg does not accept.
_UNSUPPORTED_ASYNCPG_OPTIONS = {"channel_binding"}


def normalize_database_url(url: str) -> str:
    """Accept a plain Postgres URL as a host hands it out and make it usable by SQLAlchemy + asyncpg.

    postgres:// and postgresql:// become postgresql+asyncpg://, `sslmode=` becomes asyncpg's `ssl=`,
    and libpq-only options are dropped. Other URLs (for example sqlite in tests) are left alone."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("postgres", "postgresql", "postgresql+asyncpg"):
        return url
    query = []
    for name, value in parse_qsl(parts.query, keep_blank_values=True):
        if name in _UNSUPPORTED_ASYNCPG_OPTIONS:
            continue
        query.append(("ssl" if name == "sslmode" else name, value))
    return urlunsplit(parts._replace(scheme="postgresql+asyncpg", query=urlencode(query)))


class Settings(BaseSettings):
    """Environment-driven settings. No secrets are hardcoded."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")  # works from any folder

    database_url: str
    session_secret: str
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"  # set explicitly in .env for the model you have approved
    ocr_provider: str = "tesseract"  # "google_vision" for handwriting; "tesseract" is printed-text only
    google_vision_api_key: str = ""
    google_vision_monthly_limit: int = 900  # stay under Google's 1,000 free units per month
    tesseract_min_word_confidence: float = 40.0  # 0-100; drops handwriting noise
    tesseract_cmd: str = ""  # full path to tesseract.exe if it is not on PATH (Windows)
    storage_dir: str = "./private_storage"
    cors_origins: str = "http://localhost:3000"  # comma-separated browser origins
    cookie_secure: bool = True  # set False only for local HTTP development
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 10
    openai_timeout_seconds: int = 60
    processing_timeout_seconds: int = 120
    failed_file_retention_days: int = 7
    stuck_worksheet_minutes: int = 15  # still uploaded/processing after this long = abandoned
    sweep_interval_seconds: int = 300
    login_fail_limit_email: int = 10  # failed logins per email per window before a temporary block
    login_fail_limit_ip: int = 20  # failed logins per IP address per window
    login_window_minutes: int = 15
    register_limit_ip: int = 10  # sign-up attempts per IP address per hour
    # Name of a header your own proxy sets to the real client address (e.g. "x-real-ip"). Leave empty
    # unless a trusted proxy overwrites it: otherwise anyone could fake it and dodge the limits.
    trust_proxy_header: str = ""
    max_prompt_chars: int = 12000
    # When set, every request except /health must carry this value in the X-Proxy-Secret header.
    # The Next.js proxy adds it, so the backend only answers traffic that came through the frontend.
    proxy_shared_secret: str = ""

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()  # type: ignore[call-arg]
