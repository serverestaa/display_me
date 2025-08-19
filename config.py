# config.py
import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # pydantic-settings v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",        # accept extra env vars
        case_sensitive=True,
    )

    # App
    APP_NAME: str = "Resume Builder API"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite:///./app.db"

    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost.tiangolo.com",
            "https://localhost.tiangolo.com",
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:8000",
            "https://www.displayme.online",
            "https://displayme.online",
        ]
    )

    # OAuth (no duplicates)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # Front/back URLs
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-preview-05-20"

    # Crypto
    FERNET_KEY: str = ""

    # ---- Google Cloud Storage ----
    # These are *typed* settings fields; env vars with the same names override them.
    GCS_BUCKET: str = "displayme-uploads"
    GCS_PREFIX: str = "feedback"
    # Optional: place service-account JSON directly in env (string). If unset, ADC/GOOGLE_APPLICATION_CREDENTIALS are used.
    GCS_SA_JSON: Optional[str] = None


settings = Settings()
