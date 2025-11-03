"""Integration tests for standardized API response formats."""
import pytest

# Note: client and admin_client fixtures are imported from tests.conftest automatically


@pytest.mark.integration
class TestStandardizedAuthResponses:
    """Test authentication endpoints use standardized responses."""

    def test_admin_login_success_format(self, client, monkeypatch):
        """Test admin login returns standardized success response."""
        # Set known password
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass123")

        from app.core import config
        config.settings = config.Settings()

        response = client.post(
            "/api/v1/auth/admin/login",
            json={"password": "testpass123"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should match SuccessResponse schema
        assert data["success"] is True
        assert "message" in data
        assert data["message"] == "Logged in successfully"

        # Should have only these fields
        assert set(data.keys()) == {"success", "message"}

    def test_admin_login_failure_format(self, client, monkeypatch):
        """Test admin login failure returns HTTPException format."""
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass123")

        from app.core import config
        config.settings = config.Settings()

        response = client.post(
            "/api/v1/auth/admin/login",
            json={"password": "wrongpassword"}
        )

        assert response.status_code == 401
        data = response.json()

        # FastAPI default HTTPException format
        assert "detail" in data
        assert data["detail"] == "Invalid password"

    def test_admin_logout_success_format(self, client):
        """Test admin logout returns standardized success response."""
        response = client.post("/api/v1/auth/admin/logout")

        assert response.status_code == 200
        data = response.json()

        # Should match SuccessResponse schema
        assert data["success"] is True
        assert "message" in data
        assert data["message"] == "Logged out successfully"

        # Should have only these fields
        assert set(data.keys()) == {"success", "message"}


@pytest.mark.integration
class TestStandardizedAdminResponses:
    """Test admin endpoints use standardized responses."""

    def test_delete_meeting_success_format(self, admin_client):
        """Test delete meeting returns standardized success response."""
        # First create a meeting
        create_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": "2025-12-01T10:00:00Z",
                "end_time": "2025-12-01T11:00:00Z"
            }
        )
        assert create_response.status_code == 200
        meeting_id = create_response.json()["meeting_id"]

        # Delete the meeting
        response = admin_client.delete(f"/api/v1/admin/meetings/{meeting_id}")

        assert response.status_code == 200
        data = response.json()

        # Should match SuccessResponse schema
        assert data["success"] is True
        assert "message" in data  # May be None, but field should exist
        assert set(data.keys()) == {"success", "message"}

    def test_delete_meeting_not_found_format(self, admin_client):
        """Test delete non-existent meeting returns HTTPException format."""
        response = admin_client.delete("/api/v1/admin/meetings/99999")

        assert response.status_code == 404
        data = response.json()

        # FastAPI default HTTPException format
        assert "detail" in data
        assert data["detail"] == "Meeting not found"

    def test_delete_poll_success_format(self, admin_client):
        """Test delete poll returns standardized success response."""
        # Create meeting and poll
        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": "2025-12-01T10:00:00Z",
                "end_time": "2025-12-01T11:00:00Z"
            }
        )
        meeting_id = meeting_response.json()["meeting_id"]

        poll_response = admin_client.post(
            f"/api/v1/meetings/{meeting_id}/polls",
            json={"name": "Test Poll"}
        )
        poll_id = poll_response.json()["poll_id"]

        # Delete the poll
        response = admin_client.delete(
            f"/api/v1/admin/meetings/{meeting_id}/polls/{poll_id}"
        )

        assert response.status_code == 200
        data = response.json()

        # Should match SuccessResponse schema
        assert data["success"] is True
        assert "message" in data  # May be None
        assert set(data.keys()) == {"success", "message"}


@pytest.mark.integration
class TestAPIVersioningIntegration:
    """Integration tests for API versioning headers."""

    def test_version_header_on_successful_request(self, client):
        """Test version header is present on successful requests."""
        response = client.get("/health")

        assert response.status_code == 200
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "1.0.0"

    def test_version_header_on_error_response(self, client):
        """Test version header is present even on error responses."""
        response = client.post(
            "/api/v1/auth/admin/login",
            json={"password": "wrong"}
        )

        assert response.status_code == 401
        assert "X-API-Version" in response.headers

    def test_version_header_on_all_endpoints(self, admin_client):
        """Test version header is present on various endpoints."""
        endpoints = [
            ("GET", "/health"),
            ("POST", "/api/v1/meetings/available", {}),
            ("POST", "/api/v1/auth/admin/logout", None),
        ]

        for method, url, *body in endpoints:
            if method == "GET":
                response = admin_client.get(url)
            else:
                response = admin_client.post(url, json=body[0] if body else None)

            assert "X-API-Version" in response.headers, f"Missing version header on {method} {url}"


@pytest.mark.integration
class TestResponseConsistency:
    """Test that all success responses follow the same pattern."""

    def test_all_success_responses_have_success_field(self, admin_client):
        """Test that all successful operations return success field."""
        # Logout (admin_client is already authenticated)
        logout_response = admin_client.post("/api/v1/auth/admin/logout")
        assert logout_response.json()["success"] is True

        # Create meeting (admin_client maintains auth even after logout in test)
        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": "2025-12-01T10:00:00Z",
                "end_time": "2025-12-01T11:00:00Z"
            }
        )
        # Note: This returns MeetingResponse, not SuccessResponse
        # It has meeting_id and meeting_code instead
        assert "meeting_id" in meeting_response.json()

        # Delete meeting (uses SuccessResponse)
        meeting_id = meeting_response.json()["meeting_id"]
        delete_response = admin_client.delete(f"/api/v1/admin/meetings/{meeting_id}")
        assert delete_response.json()["success"] is True

    def test_error_responses_use_detail_field(self, client, admin_client, monkeypatch):
        """Test that error responses use FastAPI's default 'detail' field."""
        # Invalid login
        monkeypatch.setenv("ADMIN_PASSWORD", "correctpass")

        from app.core import config
        config.settings = config.Settings()

        response = client.post(
            "/api/v1/auth/admin/login",
            json={"password": "wrong"}
        )
        assert response.status_code == 401
        assert "detail" in response.json()

        # Not found (using already authenticated admin_client)
        response = admin_client.delete("/api/v1/admin/meetings/99999")
        assert response.status_code == 404
        assert "detail" in response.json()


@pytest.mark.integration
class TestSchemaValidationIntegration:
    """Test that Pydantic schemas properly validate responses."""

    def test_success_response_validates_in_endpoint(self, client):
        """Test that SuccessResponse schema validation works in actual endpoint."""
        from app.schemas import SuccessResponse

        response = client.post("/api/v1/auth/admin/logout")

        # Should be valid SuccessResponse
        data = response.json()
        validated = SuccessResponse(**data)

        assert validated.success is True
        assert isinstance(validated.message, (str, type(None)))

    def test_invalid_response_would_fail_validation(self):
        """Test that invalid data fails SuccessResponse validation."""
        from app.schemas import SuccessResponse
        from pydantic import ValidationError

        # Note: 'success' has a default value of True, so it's not required
        # This test verifies that invalid types are caught

        # Invalid type for success
        with pytest.raises(ValidationError):
            SuccessResponse(**{"success": "not a boolean", "message": "test"})

        # Invalid type for message (should be string or None)
        with pytest.raises(ValidationError):
            SuccessResponse(**{"success": True, "message": 123})

        # Valid: success defaults to True if not provided
        valid = SuccessResponse(**{"message": "test"})
        assert valid.success is True
        assert valid.message == "test"
