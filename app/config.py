import os
from datetime import timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET", "your-secret-key-here")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///quorum.db")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "adminpass")
    TIMEZONE = os.getenv("APP_TIMEZONE", "America/New_York")
    TZ = ZoneInfo(TIMEZONE)
    MEETING_DURATION_HOURS = 2
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")


class ProductionConfig(Config):
    pass


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
