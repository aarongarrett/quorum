import pytest

from app import create_app
from app.database import Base, configure_database


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
    # Have to import the globals here so that they'll be given
    # real values by the configure_database step
    from app.database import SessionLocal, engine

    # Ensure the database is configured with the test settings
    # Reconfigure the database to ensure we're using the test config
    configure_database(app.config["DATABASE_URL"])

    # Drop and re-create all tables so that the schema is fresh.
    # (If you're already running Alembic migrations, replace this
    #  with an alembic upgrade head or similar.)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Create a new connection and transaction
    connection = engine.connect()
    transaction = connection.begin()

    session = SessionLocal()

    yield session

    # Cleanup: rollback the transaction and close both session & connection
    SessionLocal.remove()  # expires & closes the SessionLocal
    transaction.rollback()  # undoes all writes
    connection.close()  # returns this connection to the pool
