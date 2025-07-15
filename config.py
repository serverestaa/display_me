import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    APP_NAME: str = "Resume Builder API"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = "sqlite:///./app.db"

    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda:  [
        "http://localhost.tiangolo.com",
        "https://localhost.tiangolo.com",
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8000",
        "https://www.displayme.online",
        "https://displayme.online",
    ])

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""


    class Config:
        env_file = ".env"
        extra = "allow"
        case_sensitive = True


settings = Settings()