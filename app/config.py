import os
from datetime import timedelta
from zoneinfo import ZoneInfo


class Config:
    SECRET_KEY = os.getenv("QUORUM_FLASK_SECRET", "your-secret-key-here")
    ADMIN_PASSWORD = os.getenv("QUORUM_ADMIN_PASSWORD", "adminpass")
    TIMEZONE = os.getenv("QUORUM_TIMEZONE", "America/New_York")
    DATABASE_URL = os.getenv("QUORUM_DATABASE_URL", "sqlite:///quorum.db")
    TZ = ZoneInfo(TIMEZONE)
    MEETING_DURATION_HOURS = 2
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)


class DevelopmentConfig(Config):
    from dotenv import load_dotenv

    load_dotenv()
    DEBUG = True
    SECRET_KEY = os.getenv("QUORUM_FLASK_SECRET", "your-secret-key-here")
    ADMIN_PASSWORD = os.getenv("QUORUM_ADMIN_PASSWORD", "adminpass")
    TIMEZONE = os.getenv("QUORUM_TIMEZONE", "America/New_York")
    DATABASE_URL = os.getenv("QUORUM_DATABASE_URL", "sqlite:///quorum.db")
    TZ = ZoneInfo(TIMEZONE)


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    pass


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
