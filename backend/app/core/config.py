from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Dello API"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Base de données
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # JWT
    JWT_SECRET_KEY: SecretStr = Field(min_length=64)
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=5, le=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14, ge=1, le=30)

    # HMAC des numéros de documents
    DOCUMENT_HMAC_KEY: SecretStr = Field(min_length=64)

    # CORS (vide par défaut : l'app mobile n'en a pas besoin)
    CORS_ORIGINS: list[str] = []

    # Uploads
    MAX_UPLOAD_SIZE_MB: int = Field(default=5, ge=1, le=20)
    UPLOAD_DIR: str = "uploads"

    # Rate limiting
    AUTH_RATE_LIMIT: str = "5/minute"

    @model_validator(mode="after")
    def check_security(self) -> "Settings":
        jwt_key = self.JWT_SECRET_KEY.get_secret_value()
        hmac_key = self.DOCUMENT_HMAC_KEY.get_secret_value()

        if jwt_key == hmac_key:
            raise ValueError(
                "JWT_SECRET_KEY et DOCUMENT_HMAC_KEY doivent être différentes"
            )

        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG doit être False en production")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS ne doit pas contenir '*' en production")
            if len(self.POSTGRES_PASSWORD.get_secret_value()) < 16:
                raise ValueError(
                    "POSTGRES_PASSWORD doit faire au moins 16 caractères en production"
                )

        return self

    @property
    def database_url(self) -> str:
        password = quote_plus(self.POSTGRES_PASSWORD.get_secret_value())
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def docs_enabled(self) -> bool:
        return self.ENVIRONMENT != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()