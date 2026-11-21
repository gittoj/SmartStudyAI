from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings. No secrets are hardcoded."""

    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    session_secret: str
    openai_api_key: str = ""
    ocr_api_key: str = ""
    storage_dir: str = "./private_storage"
    cookie_secure: bool = True  # set False only for local HTTP development
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 10
    openai_timeout_seconds: int = 60


settings = Settings()  # type: ignore[call-arg]
