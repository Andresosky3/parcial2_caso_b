"""Configuración central del backend PixelForge Studio."""

from functools import lru_cache
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    """Variables de configuración cargadas desde entorno o archivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    # No dejar URL con usuario/contraseña por defecto en el código.
    # Debe venir desde backend/.env o variable de entorno DATABASE_URL.
    database_url: str = ""

    cors_allowed_origins: str = (
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