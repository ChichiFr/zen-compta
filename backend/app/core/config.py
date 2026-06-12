from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Zen Compta API"
    app_version: str = "0.1.0"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/zen_compta"
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def _fix_database_url(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v
    environment: str = "local"
    internal_api_token: str | None = None
    upload_storage_dir: str = "private_uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    openai_api_key: str | None = None
    openai_invoice_model: str = "gpt-5.5"

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")


settings = Settings()
