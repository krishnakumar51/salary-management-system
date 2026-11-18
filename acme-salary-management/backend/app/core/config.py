from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str  # pooled URL for app traffic (Neon: host contains "-pooler")
    # Direct (non-pooled) URL used by Alembic and the seed script. Optional: falls back to database_url.
    database_url_direct: str | None = None
    cors_origins: str = "http://localhost:5173"
    jwt_secret: str
    jwt_expire_minutes: int = 480

    @field_validator("database_url", "database_url_direct")
    @classmethod
    def _normalise_db_url(cls, v: str | None) -> str | None:
        if not v:
            return None
        # Neon/Heroku style URLs use postgres:// or postgresql://; force the psycopg3 driver.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @field_validator("jwt_secret")
    @classmethod
    def _secret_strength(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("JWT_SECRET must be at least 16 characters")
        return v

    @property
    def migration_database_url(self) -> str:
        """URL for DDL/bulk work: the direct connection when configured, else the app URL."""
        return self.database_url_direct or self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
