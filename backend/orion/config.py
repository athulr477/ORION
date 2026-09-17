"""Orion application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Loaded from environment variables or a `.env` file in the project root.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Async database URL (used by the application)
    database_url: str = "postgresql+asyncpg://orion:orion_secret@localhost:5432/orion_db"

    # Sync database URL (used by Alembic migrations)
    database_url_sync: str = "postgresql://orion:orion_secret@localhost:5432/orion_db"

    # JWT signing key — must be set to a non-empty value in .env
    secret_key: str = ""

    # Webhook signature secrets (HMAC-SHA256)
    jira_webhook_secret: str = ""
    github_webhook_secret: str = ""

    # Phase 7 — Ollama LLM for evidence verbalization
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # Phase 9 — GitHub App Integration
    github_app_id: int = 0
    github_app_installation_id: int = 0
    github_app_private_key_path: str = ""

    # Phase 11 — Jira REST API Integration
    jira_base_url: str = ""
    jira_user_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = "SCRUM"

    # Error tracking — leave blank to disable Sentry
    sentry_dsn: str = ""


settings = Settings()
