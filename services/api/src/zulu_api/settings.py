from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZULU_", env_file=".env", extra="ignore")

    env: str = "local"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    live_trading_enabled: bool = False
    database_url: str = Field(
        default="postgresql+psycopg://zulu:zulu_dev_password@localhost:5432/zulu"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    @property
    def live_trading_gate_summary(self) -> str:
        return "enabled" if self.live_trading_enabled else "disabled"


@lru_cache
def get_settings() -> Settings:
    return Settings()
