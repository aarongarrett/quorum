import pytest

from app import create_app
from app.database import configure_database, get_db_session


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
    # Ensure the database is configured with the test settings
    from app.database import engine

    # Reconfigure the database to ensure we're using the test config
    configure_database(app.config["DATABASE_URL"])

    # Create a new connection and transaction
    conn = engine.connect()
    trans = conn.begin()
    session = next(get_db_session())
    # set up data here
    yield session

    # Cleanup
    session.close()
    trans.rollback()
    conn.close()
