"""
SigmaCloud AI - Core Configuration
"""
import json
import logging
import os
import secrets
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)

INSECURE_JWT_PLACEHOLDER = "change-me-for-production"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SigmaCloud AI"
    VERSION: str = "1.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./sigmacloud.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_RECYCLE_SECONDS: int = 1800

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Storage
    BASE_STORAGE_PATH: str = "./backend/storage"
    MODEL_STORAGE_PATH: str = "./backend/storage/models"
    DATASET_STORAGE_PATH: str = "./backend/storage/datasets"

    # Logging - file logging is off by default because hosts like Render use
    # ephemeral disks and already capture stdout.
    LOG_TO_FILE: bool = False

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]
    ALLOWED_ORIGIN_REGEX: str = ""

    # Auth
    JWT_SECRET_KEY: str = INSECURE_JWT_PLACEHOLDER
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLOCK_SKEW_SECONDS: int = 10

    # Uploads
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024

    # ML Config
    MAX_TRAINING_TIME_SECONDS: int = 900
    CV_FOLDS: int = 5
    TEST_SIZE: float = 0.2
    RANDOM_STATE: int = 42
    # Any job left running longer than this is treated as killed by a restart
    # (free hosting tiers spin services down mid-job).
    STALE_JOB_TIMEOUT_MINUTES: int = 30

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        if isinstance(value, list):
            return value

        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []

            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass

            return [item.strip() for item in raw.split(",") if item.strip()]

        return value

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value):
        """Render/Heroku hand out `postgres://`, which SQLAlchemy 2.x rejects."""
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @model_validator(mode="after")
    def enforce_production_secrets(self):
        is_production = self.ENVIRONMENT.lower() in {"production", "prod"}

        if self.JWT_SECRET_KEY == INSECURE_JWT_PLACEHOLDER:
            if is_production:
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a unique random value when "
                    "ENVIRONMENT=production. Generate one with: "
                    "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
            # Dev convenience: a random per-boot secret is safer than a known
            # constant. Sessions do not survive a restart, which is fine locally.
            self.JWT_SECRET_KEY = secrets.token_urlsafe(48)
            logger.warning(
                "JWT_SECRET_KEY not set - generated an ephemeral development secret. "
                "Sessions will not survive a restart."
            )

        return self

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.MODEL_STORAGE_PATH, exist_ok=True)
os.makedirs(settings.DATASET_STORAGE_PATH, exist_ok=True)
