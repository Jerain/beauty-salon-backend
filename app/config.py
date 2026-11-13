"""Application configuration loaded from environment variables."""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/beauty_salon"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/beauty_salon"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "beauty-salon-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:5174"

    # App
    app_name: str = "Beauty Salon Backend"
    app_version: str = "0.1.0"
    debug: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
