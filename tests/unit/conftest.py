import pytest
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.database import db as _db


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def db(app):
    _db.drop_all()
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
def db_connection(session):
    """For backward compatibility."""
    return session
