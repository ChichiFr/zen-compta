from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Zen Compta API"
    app_version: str = "0.1.0"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/zen_compta"
    )
    environment: str = "local"
    internal_api_token: str | None = None
    upload_storage_dir: str = "private_uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    openai_api_key: str | None = None
    openai_invoice_model: str = "gpt-5.5"
    gocardless_secret_id: str | None = None
    gocardless_secret_key: str | None = None
    gocardless_redirect_uri: str = "http://localhost:3000/bank/callback"
    powens_client_id: str | None = None
    powens_client_secret: str | None = None
    powens_domain: str | None = None
    bank_aggregator_provider: str = "powens"
    plaid_client_id: str | None = None
    plaid_secret: str | None = None
    plaid_env: str = "sandbox"

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")


settings = Settings()
