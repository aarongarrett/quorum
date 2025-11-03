"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional, Union
import os

from app.core.constants import ACCESS_TOKEN_EXPIRE_MINUTES as DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Database - Support both full URL and individual components
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ADMIN_PASSWORD: str = "adminpass"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES

    # CORS - Can be a list or comma-separated string
    CORS_ORIGINS: Union[list, str] = ["*"]  # In production, specify your domain

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list."""
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v

    # Application
    APP_TITLE: str = "Quorum Voting System"
    APP_DESCRIPTION: str = "Anonymous QR-driven voting for meetings"
    APP_VERSION: str = "1.0.0"

    # Frontend
    FRONTEND_BUILD_PATH: str = "./frontend/build"

    # Environment
    ENVIRONMENT: str = "development"  # development, staging, production

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Server-Sent Events (SSE) Configuration
    SSE_USER_INTERVAL: int = 5  # User-facing meeting list updates every 5 seconds
    SSE_ADMIN_INTERVAL: int = 3  # Admin dashboard updates every 3 seconds (faster for real-time monitoring)

    # Database Connection Pool Configuration
    DB_POOL_SIZE: int = 15  # Steady-state connection pool size (200 users polling every 5s)
    DB_MAX_OVERFLOW: int = 25  # Additional connections for spikes (total max: pool_size + max_overflow)

    def get_database_url(self) -> str:
        """
        Get database URL from either DATABASE_URL or individual components.
        Priority: DATABASE_URL > individual components > default (dev only)
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL

        # Build from individual components if provided
        if all([self.POSTGRES_USER, self.POSTGRES_PASSWORD,
                self.POSTGRES_HOST, self.POSTGRES_DB]):
            port = self.POSTGRES_PORT or "5432"
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{port}/{self.POSTGRES_DB}"
            )

        # Development fallback only
        if self.ENVIRONMENT == "development":
            return "postgresql://quorum:quorum@localhost:5432/quorum"

        # Production should always provide database credentials
        raise ValueError(
            "Database configuration missing. Provide either DATABASE_URL or "
            "all of: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DB"
        )

    def validate_production_config(self) -> None:
        """Validate that production-critical settings are properly configured."""
        if self.ENVIRONMENT == "production":
            issues = []
            warnings = []

            if self.SECRET_KEY == "your-secret-key-change-in-production":
                issues.append("SECRET_KEY must be changed from default value")

            if self.ADMIN_PASSWORD == "adminpass":
                issues.append("ADMIN_PASSWORD must be changed from default value")

            # Warn if password is not hashed (starts with $argon2)
            if not self.ADMIN_PASSWORD.startswith("$argon2"):
                warnings.append(
                    "ADMIN_PASSWORD is not hashed. For better security, use:\n"
                    "    python -c \"from app.core.security import get_password_hash; "
                    "print(get_password_hash('your-password'))\""
                )

            if self.CORS_ORIGINS == ["*"]:
                issues.append("CORS_ORIGINS should be restricted to specific domains")

            if warnings:
                print("⚠️  Production configuration warnings:")
                for warning in warnings:
                    print(f"  - {warning}")

            if issues:
                raise ValueError(
                    "Production configuration errors:\n" +
                    "\n".join(f"  - {issue}" for issue in issues)
                )


settings = Settings()

# Validate production configuration on startup
if os.getenv("ENVIRONMENT") == "production":
    settings.validate_production_config()
