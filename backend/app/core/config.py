import os
from functools import lru_cache
from pathlib import Path

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_project_env() -> None:
    project_root = Path(__file__).resolve().parents[3]
    candidates = [
        project_root / ".env",
        project_root / "backend" / ".env",
        project_root / "contracts" / ".env",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        with candidate.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)


_load_project_env()


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
    scheduler_enabled: bool = Field(default=True, validation_alias="SCHEDULER_ENABLED")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    seace_timeout_seconds: float = Field(default=20.0, validation_alias="SEACE_TIMEOUT_SECONDS")
    seace_max_retries: int = Field(default=3, validation_alias="SEACE_MAX_RETRIES")
    api_default_page_size: int = 50
    api_max_page_size: int = 200
    zktanenbaum_rpc_url: AnyUrl = Field(
        default="https://rpc-zk.tanenbaum.io",
        validation_alias="ZKTANENBAUM_RPC_URL",
    )
    zktanenbaum_chain_id: int = Field(default=57057, validation_alias="ZKTANENBAUM_CHAIN_ID")
    identity_contract_address: str | None = Field(default=None, validation_alias="IDENTITY_CONTRACT_ADDRESS")
    identity_anchor_private_key: str | None = Field(default=None, validation_alias="IDENTITY_ANCHOR_PRIVATE_KEY")
    identity_explorer_base_url: str | None = Field(
        default="https://explorer.zktanenbaum.io/tx",
        validation_alias="IDENTITY_EXPLORER_BASE_URL",
    )
    identity_token_secret: str = Field(
        default="change-me-in-production",
        validation_alias="IDENTITY_TOKEN_SECRET",
    )
    identity_token_ttl_seconds: int = Field(
        default=60 * 60 * 24 * 30,
        validation_alias="IDENTITY_TOKEN_TTL_SECONDS",
    )
    identity_nonce_ttl_seconds: int = Field(
        default=60 * 10,
        validation_alias="IDENTITY_NONCE_TTL_SECONDS",
    )

    @field_validator("crawler_interval")
    @classmethod
    def validate_crawler_interval(cls, value: int) -> int:
        if value < 60:
            raise ValueError("CRAWLER_INTERVAL must be at least 60 seconds")
        return value

    @field_validator("identity_token_ttl_seconds", "identity_nonce_ttl_seconds")
    @classmethod
    def validate_positive_ttl(cls, value: int) -> int:
        if value < 1:
            raise ValueError("TTL settings must be positive")
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
