"""Application configuration and settings.

Uses Pydantic Settings for type-safe configuration management with
environment variable support.
"""

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")

    # Security settings
    secret_key: str = Field(
        default="change_me_generate_with_openssl_dev_only",
        alias="SECRET_KEY",
    )
    access_token_expire_minutes: int = Field(
        default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
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
                secret is too short.
        """
        app_env = info.data.get("app_env", "development")

        if (
            app_env == "production"
            and v == "change_me_generate_with_openssl_dev_only"
        ):
            raise ValueError(
                "SECRET_KEY must be set for production environment. "
                "Generate one with: openssl rand -hex 32"
            )

        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")

        return v


settings = Settings()
