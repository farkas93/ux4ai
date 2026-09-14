from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./aipm_toolkit.db"
    session_ttl_hours: int = 12
    cookie_name: str = "aipm_session"
    cookie_secure: bool = False
    rate_limit_failures: int = 5
    rate_limit_window_seconds: int = 300
    rate_limit_lockout_seconds: int = 30

    model_config = SettingsConfigDict(env_prefix="AIPM_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
