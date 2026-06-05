import os
from functools import lru_cache

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=None if os.getenv("ENVIRONMENT", "").lower() in {"prod", "production"} else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SEACE Opportunities API"
    app_version: str = "1.0.0"
    environment: str = "production"
    database_url: str = Field(
        default="postgresql+asyncpg://seace:seace@postgres:5432/seace",
        validation_alias="DATABASE_URL",
    )
    seace_base_url: AnyUrl = Field(
        default="https://prod4.seace.gob.pe:8086",
        validation_alias="SEACE_BASE_URL",
    )
    crawler_interval: int = Field(default=3600, validation_alias="CRAWLER_INTERVAL")
    crawler_keywords: str = Field(
        default="software,cloud,firewall,ciberseguridad",
        validation_alias="CRAWLER_KEYWORDS",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    seace_timeout_seconds: float = Field(default=20.0, validation_alias="SEACE_TIMEOUT_SECONDS")
    seace_max_retries: int = Field(default=3, validation_alias="SEACE_MAX_RETRIES")
    api_default_page_size: int = 50
    api_max_page_size: int = 200

    @field_validator("crawler_interval")
    @classmethod
    def validate_crawler_interval(cls, value: int) -> int:
        if value < 60:
            raise ValueError("CRAWLER_INTERVAL must be at least 60 seconds")
        return value

    @property
    def scheduler_keywords(self) -> list[str]:
        return [keyword.strip() for keyword in self.crawler_keywords.split(",") if keyword.strip()]

    @property
    def sync_database_url(self) -> str:
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
