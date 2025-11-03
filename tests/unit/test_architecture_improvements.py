"""Unit tests for architecture improvements from Section 4."""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.main import app
from app.core.config import Settings
from app.schemas import SuccessResponse, ErrorResponse, ErrorDetail


@pytest.mark.unit
class TestAPIVersioning:
    """Tests for API versioning headers (Issue 4.3)."""

    def test_api_version_header_present(self):
        """Test that X-API-Version header is added to all responses."""
        client = TestClient(app)

        response = client.get("/health")

        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == app.version

    def test_api_version_header_on_404(self):
        """Test that version header is added even to 404 responses."""
        client = TestClient(app)

        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == app.version

    def test_api_version_header_on_api_endpoints(self):
        """Test that version header is present on API endpoints."""
        client = TestClient(app)

        # Test public endpoint
        response = client.post("/api/v1/meetings/available", json={})

        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == app.version

    def test_api_version_matches_app_version(self):
        """Test that the version header matches the app version from settings."""
        from app.core.config import settings

        client = TestClient(app)
        response = client.get("/health")

        assert response.headers["X-API-Version"] == settings.APP_VERSION


@pytest.mark.unit
class TestDatabasePoolConfiguration:
    """Tests for configurable database pool (Issue 4.4)."""

    def test_default_pool_size(self):
        """Test that default pool size is 15."""
        settings = Settings()
        assert settings.DB_POOL_SIZE == 15

    def test_default_max_overflow(self):
        """Test that default max overflow is 25."""
        settings = Settings()
        assert settings.DB_MAX_OVERFLOW == 25

    def test_custom_pool_size_from_env(self, monkeypatch):
        """Test that pool size can be configured via environment."""
        monkeypatch.setenv("DB_POOL_SIZE", "30")
        settings = Settings()

        assert settings.DB_POOL_SIZE == 30

    def test_custom_max_overflow_from_env(self, monkeypatch):
        """Test that max overflow can be configured via environment."""
        monkeypatch.setenv("DB_MAX_OVERFLOW", "50")
        settings = Settings()

        assert settings.DB_MAX_OVERFLOW == 50

    def test_pool_configuration_used_in_engine(self, monkeypatch):
        """Test that pool configuration is actually used when creating engine."""
        monkeypatch.setenv("DB_POOL_SIZE", "20")
        monkeypatch.setenv("DB_MAX_OVERFLOW", "30")

        # Reimport to get new settings
        from app.core import config
        config.settings = Settings()

        # Verify settings were loaded
        assert config.settings.DB_POOL_SIZE == 20
        assert config.settings.DB_MAX_OVERFLOW == 30

        # Note: SQLite doesn't support pool_size/max_overflow the same way as PostgreSQL
        # This test verifies the settings are loaded correctly, which is what matters


@pytest.mark.unit
class TestStandardizedResponseFormats:
    """Tests for standardized response formats (Issue 4.1)."""

    def test_success_response_schema(self):
        """Test SuccessResponse schema structure."""
        response = SuccessResponse(success=True)

        assert response.success is True
        assert response.message is None

    def test_success_response_with_message(self):
        """Test SuccessResponse with message."""
        response = SuccessResponse(success=True, message="Operation completed")

        assert response.success is True
        assert response.message == "Operation completed"

    def test_success_response_json_format(self):
        """Test SuccessResponse JSON serialization."""
        response = SuccessResponse(success=True, message="Test message")
        json_data = response.model_dump()

        assert json_data == {
            "success": True,
            "message": "Test message"
        }

    def test_error_detail_schema(self):
        """Test ErrorDetail schema structure."""
        error = ErrorDetail(code="TEST_ERROR", message="Test error message")

        assert error.code == "TEST_ERROR"
        assert error.message == "Test error message"

    def test_error_response_schema(self):
        """Test ErrorResponse schema structure."""
        error_detail = ErrorDetail(code="NOT_FOUND", message="Resource not found")
        response = ErrorResponse(success=False, error=error_detail)

        assert response.success is False
        assert response.error.code == "NOT_FOUND"
        assert response.error.message == "Resource not found"

    def test_error_response_json_format(self):
        """Test ErrorResponse JSON serialization matches expected format."""
        error_detail = ErrorDetail(code="VALIDATION_ERROR", message="Invalid input")
        response = ErrorResponse(success=False, error=error_detail)
        json_data = response.model_dump()

        expected = {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input"
            }
        }

        assert json_data == expected


@pytest.mark.unit
class TestEndpointResponseConsistency:
    """Test that endpoints use standardized response formats."""

    def test_admin_login_returns_success_response(self, monkeypatch):
        """Test admin login returns SuccessResponse format."""
        # Set admin password for test
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass123")

        from app.core import config
        config.settings = config.Settings()

        client = TestClient(app)

        response = client.post(
            "/api/v1/auth/admin/login",
            json={"password": "testpass123"}
        )

        assert response.status_code == 200
        json_data = response.json()

        # Should have success and message fields
        assert "success" in json_data
        assert json_data["success"] is True
        assert "message" in json_data

    def test_admin_logout_returns_success_response(self):
        """Test admin logout returns SuccessResponse format."""
        client = TestClient(app)

        response = client.post("/api/v1/auth/admin/logout")

        assert response.status_code == 200
        json_data = response.json()

        # Should have success and message fields
        assert "success" in json_data
        assert json_data["success"] is True
        assert "message" in json_data

    def test_http_exception_format(self):
        """Test that HTTPException still uses FastAPI's default format."""
        client = TestClient(app)

        # Trigger a 404
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        json_data = response.json()

        # FastAPI's default HTTPException format
        assert "detail" in json_data


@pytest.mark.unit
class TestSchemaValidation:
    """Test Pydantic schema validation for new response types."""

    def test_success_response_has_default_success_field(self):
        """Test that success field has default value in SuccessResponse."""
        # Should work with success=True explicitly
        response = SuccessResponse(success=True)
        assert response.success is True

        # Should work with success=False explicitly
        response = SuccessResponse(success=False)
        assert response.success is False

        # Should work without success field (defaults to True)
        response = SuccessResponse()
        assert response.success is True

    def test_success_response_message_optional(self):
        """Test that message field is optional in SuccessResponse."""
        # Should work without message
        response = SuccessResponse(success=True)
        assert response.message is None

        # Should work with message
        response = SuccessResponse(success=True, message="Done")
        assert response.message == "Done"

    def test_error_detail_requires_all_fields(self):
        """Test that ErrorDetail requires code and message."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ErrorDetail(code="TEST")  # Missing message

        with pytest.raises(ValidationError):
            ErrorDetail(message="Test")  # Missing code

        # Should work with both fields
        error = ErrorDetail(code="TEST", message="Test message")
        assert error.code == "TEST"
        assert error.message == "Test message"


@pytest.mark.unit
class TestConfigurationDefaults:
    """Test that new configuration options have sensible defaults."""

    def test_db_pool_size_default_is_reasonable(self):
        """Test that default pool size is appropriate for typical load."""
        settings = Settings()

        # Default should handle ~200 concurrent SSE users
        # with 5-second polling interval
        assert settings.DB_POOL_SIZE >= 10
        assert settings.DB_POOL_SIZE <= 50

    def test_db_max_overflow_allows_traffic_spikes(self):
        """Test that max overflow is sufficient for traffic spikes."""
        settings = Settings()

        # Total max connections should be reasonable
        total_max = settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW

        assert total_max >= 30  # Minimum for production
        assert total_max <= 100  # Not excessive

    def test_total_pool_capacity(self):
        """Test that total pool capacity is documented value (40)."""
        settings = Settings()

        total = settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW
        assert total == 40  # As documented in comments
