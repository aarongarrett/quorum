"""Shared test fixtures and configuration."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.main import app
from app.db.base import Base
from app.api.deps import get_db
from app.core.security import create_access_token


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def disable_rate_limiting_for_tests(request):
    """Disable rate limiting for all tests except rate limiting tests."""
    from app.core.rate_limit import limiter

    # Check if this is a rate limiting test (marked with @pytest.mark.rate_limit)
    if "rate_limit" in request.keywords:
        # For rate limit tests, reset the limiter state before test
        limiter.reset()
        yield
        # Clean up after rate limit test
        limiter.reset()
    else:
        # Disable rate limiting for all other tests
        with patch('app.core.rate_limit.limiter.limit', lambda *args, **kwargs: lambda func: func):
            yield

@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh database for each test."""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for a test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with a test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token():
    """Generate a valid admin JWT token."""
    return create_access_token({"is_admin": True})


@pytest.fixture
def admin_client(client, admin_token):
    """Create a test client with admin cookie already set."""
    # Set the admin token as a cookie
    client.cookies.set("admin_token", admin_token)
    return client
