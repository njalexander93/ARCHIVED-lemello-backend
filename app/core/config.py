"""Application configuration and settings.

Uses Pydantic Settings for type-safe configuration management with
environment variable support.
"""

from enum import Enum
from typing import Optional

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment enumeration."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def _missing_(cls, value: object) -> Optional["Environment"]:
        """Handle case-insensitive lookup of environment values.

        Returns:
            The matching Environment member for a case-insensitive value,
            or None if the value is invalid so that validation fails fast.
        """
        if isinstance(value, str):
            value = value.lower()
            for member in cls:
                if member.value.lower() == value:
                    return member
        return None


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        app_env: Application environment (development, staging, production).
        app_debug: Debug mode flag for development.
        secret_key: JWT signing key for authentication.
        access_token_expire_minutes: JWT token expiration time in minutes.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_env: Environment = Field(
        default=Environment.DEVELOPMENT, alias="APP_ENV"
    )
    app_debug: bool = Field(default=False, alias="APP_DEBUG")

    # Security settings
    secret_key: str = Field(
        default="change_me_generate_with_openssl_dev_only",
        alias="SECRET_KEY",
    )
    access_token_expire_minutes: int = Field(
        default=60,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
        ge=1,
        le=10080,  # Max 1 week
    )

    # Database settings
    database_url: Optional[str] = Field(
        default=None,
        alias="DATABASE_URL",
        description="PostgreSQL connection string",
    )

    # Redis settings
    redis_url: Optional[str] = Field(
        default=None, alias="REDIS_URL", description="Redis connection string"
    )

    # OpenAI / AI Configuration
    openai_api_key: Optional[str] = Field(
        default=None, alias="OPENAI_API_KEY", description="OpenAI API key"
    )
    ai_model: str = Field(default="gpt-4o", alias="AI__MODEL")
    ai_temperature: float = Field(
        default=0.7, alias="AI__TEMPERATURE", ge=0.0, le=1.0
    )
    ai_max_tokens: int = Field(
        default=2048, alias="AI__MAX_TOKENS", ge=1, le=128000
    )
    ai_max_retries: int = Field(default=3, alias="AI__MAX_RETRIES", ge=0)
    ai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="AI__EMBEDDING_MODEL"
    )

    # Vector Search / RAG
    vector_dimensions: int = Field(
        default=1536, alias="VECTOR_DIMENSIONS", ge=1
    )
    rag_top_k_records: int = Field(
        default=5, alias="RAG_TOP_K_RECORDS", ge=1, le=100
    )

    # Logging & Observability
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="TEXT", alias="LOG_FORMAT")
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    otel_endpoint: Optional[str] = Field(default=None, alias="OTEL_ENDPOINT")
    otel_service_name: str = Field(
        default="lemello-backend", alias="OTEL_SERVICE_NAME"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """Ensure production uses a secure secret key.

        Args:
            v: The secret key value to validate.
            info: Validation context containing other field values.

        Returns:
            The validated secret key.

        Raises:
            ValueError: If production environment uses default secret or if
                secret is too short or predictable.
        """
        app_env = info.data.get("app_env", Environment.DEVELOPMENT)

        # Reject placeholder values in production and staging
        if app_env in (
            Environment.PRODUCTION,
            Environment.STAGING,
        ) and v.lower().startswith("change_me"):
            raise ValueError(
                "SECRET_KEY must be set for production/staging environments. "
                "Generate one with: openssl rand -hex 32"
            )

        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")

        # Check for obvious weak patterns
        if all(c == v[0] for c in v):  # All same character
            raise ValueError("SECRET_KEY must not be a repeating pattern")

        weak_keys = [
            "a" * 32,
            "1" * 32,
            "0" * 32,
            "password" * 4,
            "change_me_generate_with_openssl" + "a" * 4,
        ]
        if v.lower() in [k.lower() for k in weak_keys]:
            raise ValueError("SECRET_KEY is too predictable")

        return v


settings = Settings()
