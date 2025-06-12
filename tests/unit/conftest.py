import os

import pytest
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker
from testcontainers.postgres import PostgresContainer

from app import create_app
from app.database import db as _db


@pytest.fixture(scope="session")  # start a real Postgres container once
def pg_container():
    """
    Spin up a throwaway Postgres container for the test session.
    """
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def app(pg_container):
    """
    Create the Flask app configured to use the Postgres container.
    """
    # Point at our container
    os.environ["QUORUM_DATABASE_URL"] = pg_container.get_connection_url()
    app = create_app("testing")
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def db(app):
    """
    Create all tables before tests and drop them when session ends.
    """
    _db.create_all()
    yield _db
    _db.session.remove()
    _db.drop_all()


@pytest.fixture(scope="function")
def session(db):
    connection = db.engine.connect()
    transaction = connection.begin()

    scoped = scoped_session(sessionmaker(bind=connection))

    nested = connection.begin_nested()

    @event.listens_for(scoped(), "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    db.session = scoped

    try:
        yield scoped
    finally:
        scoped.remove()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(app, session):
    # Ensure the client uses the same context and DB session
    return app.test_client()


@pytest.fixture(scope="function")
def authenticated_client(client):
    """Create a test client that is authenticated as an admin."""
    with client.session_transaction() as sess:
        sess["is_admin"] = True
    return client


@pytest.fixture
def db_session(session):
    """For backward compatibility."""
    return session
