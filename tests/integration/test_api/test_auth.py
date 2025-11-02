"""Integration tests for authentication API."""
import pytest


@pytest.mark.integration
class TestAdminAuth:
    """Test admin authentication endpoints."""

    def test_admin_login_success(self, client, monkeypatch):
        """Valid password should set JWT token in cookie."""
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass123")

        # Reload settings and security module
        from app.core import config, security
        import importlib
        importlib.reload(config)
        importlib.reload(security)

        response = client.post(
            "/api/v1/auth/admin/login",
            json={"password": "testpass123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Check that admin_token cookie was set
        assert "admin_token" in response.cookies

    def test_admin_login_invalid_password(self, client, monkeypatch):
        """Invalid password should return 401."""
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass123")

        from app.core import config, security
        import importlib
        importlib.reload(config)
        importlib.reload(security)

        response = client.post(
            "/api/v1/auth/admin/login",
            json={"password": "wrongpassword"}
        )

        assert response.status_code == 401
        assert "detail" in response.json()
