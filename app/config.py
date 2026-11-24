from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./shortener.db"
    base_url: str = "http://localhost:8000"
    code_length: int = 6
    max_url_length: int = 2048
    allowed_hosts: str = ""  # comma-separated; empty means any host

    # Admin panel (HTTP Basic). Leave the password empty to disable the admin panel.
    admin_username: str = "admin"
    admin_password: str = ""

    # Max link creations per client IP per minute (0 = unlimited).
    rate_limit_per_minute: int = 30

    @property
    def allowed_host_set(self) -> set[str]:
        return {h.strip().lower() for h in self.allowed_hosts.split(",") if h.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
