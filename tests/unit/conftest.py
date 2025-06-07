import pytest

from app import create_app
from app.database import db


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    """Create a test client that is authenticated as an admin."""
    with client.session_transaction() as session:
        session["is_admin"] = True
    return client


@pytest.fixture
def db_connection(app):
    """Provide a clean database session for a test."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield db.session
        db.session.rollback()
