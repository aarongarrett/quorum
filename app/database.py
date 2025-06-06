import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.orm.session import Session as SessionType

# Globals for engine and session factory
engine: Optional[Engine] = None
SessionLocal: Optional[scoped_session[SessionType]] = None


# Function to configure the database (for test or prod)
def configure_database(uri: Optional[str] = None) -> None:
    global engine, SessionLocal
    if uri is None:
        uri = os.environ.get("DATABASE_URL", "sqlite:///quorum.db")

    connect_args = {}
    if uri.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        uri,
        connect_args=connect_args,
        echo=False,  # Set to True for SQL query logging
    )
    SessionLocal = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )


def get_db_session() -> Iterator[Session]:
    """Yield a new SQLAlchemy Session, then close."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call configure_database() first.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    for db in get_db_session():
        try:
            yield db
        finally:
            # the generator’s finally already calls db.close(),
            # so we don’t need to do it again here
            pass
