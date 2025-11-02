"""Database session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from app.core.config import settings

DATABASE_URL = settings.get_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    pool_size=15,        # Steady-state SSE load (200 users polling every 5s)
    max_overflow=25      # Handle vote spikes + variance (total max: 40 connections)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for getting database session outside of FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
