import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mode: Literal["web", "desktop"] = "web"
    data_dir: Path | None = None
    database_url: str = "sqlite:///./aipm_toolkit.db"
    session_ttl_hours: int = 12
    cookie_name: str = "aipm_session"
    cookie_secure: bool = False
    rate_limit_failures: int = 5
    rate_limit_window_seconds: int = 300
    rate_limit_lockout_seconds: int = 30
    password_concurrency_limit: int = Field(default=4, ge=1, le=32)
    session_touch_interval_seconds: int = Field(default=60, ge=0)
    ui_concurrency_limit: int = Field(default=8, ge=1, le=40)

    model_config = SettingsConfigDict(env_prefix="AIPM_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    if os.getenv("AIPM_MODE") == "desktop":
        # Desktop bootstrap controls storage before any engine/UI imports.
        # An unrelated .env or a deployment DATABASE_URL must not redirect it.
        return Settings(
            _env_file=None,
            mode="desktop",
            data_dir=Path(os.environ["AIPM_DATA_DIR"]).resolve(),
            database_url="sqlite://",
            cookie_name="aipm_session",
            cookie_secure=False,
        )
    return Settings()
