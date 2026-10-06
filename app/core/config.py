from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./progress.db"
    UPLOAD_DIR: str = "./uploads"
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 7
    RESET_TOKEN_MINUTES: int = 30
    BCRYPT_ROUNDS: int = 12
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    FRONTEND_RESET_PATH: str = "/reset-password"
    MAX_UPLOAD_MB: int = 10
    TOTAL_CHAPTERS: int = 5
    INACTIVITY_DAYS: int = 21
    BACKUP_KEEP: int = 7
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = "no-reply@localhost"
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH: str = "5/minute"
    MAINTENANCE_ENABLED: bool = True

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.FRONTEND_ORIGIN.split(",") if o.strip()]

    @property
    def backup_dir(self) -> Path:
        return Path(self.UPLOAD_DIR).resolve().parent / "backups"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
