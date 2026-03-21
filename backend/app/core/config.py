"""Core configuration using pydantic-settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень проекта (папка, в которой лежит backend/) — оттуда грузим .env при локальном запуске
# config.py: backend/app/core/ -> 3 уровня вверх = backend, ещё 1 = корень
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
_MEDIA_ROOT = _PROJECT_ROOT / "backend" / "media"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/news_platform"
    database_url_sync: str = "postgresql://postgres:postgres@postgres:5432/news_platform"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # Security
    secret_key: str = "change-me-to-a-random-secret-key-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"
    allow_public_registration: bool = False
    bootstrap_admin_email: str | None = None
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None
    seed_demo_content: bool = False

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # AI
    ai_provider: Literal["gemini", "openai", "openrouter", "yandex"] = "gemini"
    gemini_api_key: str = ""
    gemini_image_model: str = "gemini-2.5-flash-image"
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    yandex_text_model: str = "gpt://default"
    yandex_image_model: str = "art://default"
    enable_ai_images: bool = False

    # Telegram
    telegram_api_id: str = ""
    telegram_api_hash: str = ""
    telegram_session_string: str = ""
    telegram_bot_token: str = ""
    telegram_publish_channel_id: str = ""

    # VK
    vk_access_token: str = ""

    # Collection
    collection_interval_minutes: int = 60

    # Automation
    auto_approve_enabled: bool = False
    auto_publish_enabled: bool = False
    auto_publish_targets: str = "website"
    auto_publish_max_per_run: int = 0

    # Backend
    backend_url: str = "http://localhost:8000"
    public_site_url: str = "http://localhost:3000"
    media_root: str = str(_MEDIA_ROOT)

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        default_creds = {
            "admin@example.com",
            "admin",
            "admin123",
            "change-me-to-a-random-secret-key-in-production",
        }

        if self.app_env == "production":
            if self.secret_key in default_creds:
                raise ValueError("SECRET_KEY must be changed in production")
            if self.seed_demo_content:
                raise ValueError("SEED_DEMO_CONTENT must be disabled in production")
            if {
                self.bootstrap_admin_email,
                self.bootstrap_admin_username,
                self.bootstrap_admin_password,
            } & default_creds:
                raise ValueError("Default bootstrap admin credentials are not allowed in production")

        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def auto_publish_targets_list(self) -> list[str]:
        return [target.strip() for target in self.auto_publish_targets.split(",") if target.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
