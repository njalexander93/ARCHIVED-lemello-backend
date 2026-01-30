"""Application configuration and settings.

Uses Pydantic Settings for type-safe configuration management with
environment variable support.
"""

from pydantic import Field
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
        default="change_me_generate_with_openssl", alias="SECRET_KEY"
    )
    access_token_expire_minutes: int = Field(
        default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )


settings = Settings()
