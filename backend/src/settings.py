"""Configuración central del backend PixelForge Studio."""

import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


load_dotenv()


class Settings(BaseSettings):
    app_env: str = os.getenv("APP_ENV", "local")

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://game_app:PixelForge_Final_DB_2026*@localhost:5433/pixelforge_final_db"
    )

    cors_allowed_origins: str = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:4200,http://127.0.0.1:4200"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()