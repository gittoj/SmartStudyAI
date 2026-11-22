from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


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
    max_prompt_chars: int = 12000

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()  # type: ignore[call-arg]
