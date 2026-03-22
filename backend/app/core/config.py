"""
SigmaCloud AI - Core Configuration
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SigmaCloud AI"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./sigmacloud.db"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Storage
    BASE_STORAGE_PATH: str = "./backend/storage"
    MODEL_STORAGE_PATH: str = "./backend/storage/models"
    DATASET_STORAGE_PATH: str = "./backend/storage/datasets"

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

    # Auth
    JWT_SECRET_KEY: str = "change-me-for-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLOCK_SKEW_SECONDS: int = 10

    # ML Config
    MAX_TRAINING_TIME_SECONDS: int = 300
    CV_FOLDS: int = 5
    TEST_SIZE: float = 0.2
    RANDOM_STATE: int = 42

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.MODEL_STORAGE_PATH, exist_ok=True)
os.makedirs(settings.DATASET_STORAGE_PATH, exist_ok=True)
