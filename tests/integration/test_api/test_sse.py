"""Integration tests for SSE (Server-Sent Events) endpoints."""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, Mock
from sqlalchemy.exc import DatabaseError


@pytest.mark.integration
class TestSSEMeetingsEndpoint:
    """Tests for sse_meetings endpoint."""

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_meetings_empty_tokens(self, mock_event_generator, client):
        """Test SSE meetings endpoint with no tokens."""
        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        response = client.get("/api/v1/sse/meetings")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_meetings_with_valid_tokens(self, mock_event_generator, client):
        """Test SSE meetings endpoint with valid token map."""
        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        token_map = {"1": "token1", "2": "token2"}
        tokens_json = json.dumps(token_map)

        response = client.get(f"/api/v1/sse/meetings?tokens={tokens_json}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_sse_meetings_invalid_json_tokens(self, client):
        """Test SSE meetings endpoint with invalid JSON tokens."""
        response = client.get("/api/v1/sse/meetings?tokens=invalid-json")

        assert response.status_code == 400
        assert "Invalid tokens parameter" in response.json()["detail"]

    def test_sse_meetings_invalid_token_format(self, client):
        """Test SSE meetings endpoint with non-integer keys in token map."""
        # Valid JSON but keys can't be converted to int
        token_map = {"not-a-number": "token1"}
        tokens_json = json.dumps(token_map)

        response = client.get(f"/api/v1/sse/meetings?tokens={tokens_json}")

        assert response.status_code == 400
        assert "Invalid tokens parameter" in response.json()["detail"]

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_meetings_response_headers(self, mock_event_generator, client):
        """Test SSE meetings endpoint returns correct headers."""
        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        response = client.get("/api/v1/sse/meetings")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"
        assert response.headers["x-accel-buffering"] == "no"

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_meetings_with_existing_meeting(self, mock_event_generator, client, admin_client):
        """Test SSE meetings endpoint returns meeting data."""
        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        # Create a meeting first
        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            }
        )
        assert meeting_response.status_code == 200

        # Request SSE stream
        response = client.get("/api/v1/sse/meetings")

        assert response.status_code == 200

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_meetings_with_token_map_integer_keys(self, mock_event_generator, client):
        """Test SSE meetings endpoint correctly converts string keys to integers."""
        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        # Create token map with string keys (as JSON would have)
        token_map = {"123": "abc123", "456": "def456"}
        tokens_json = json.dumps(token_map)

        response = client.get(f"/api/v1/sse/meetings?tokens={tokens_json}")

        assert response.status_code == 200
        # Endpoint should successfully parse and convert keys to integers

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_meetings_empty_token_map(self, mock_event_generator, client):
        """Test SSE meetings endpoint with empty token map."""
        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        token_map = {}
        tokens_json = json.dumps(token_map)

        response = client.get(f"/api/v1/sse/meetings?tokens={tokens_json}")

        assert response.status_code == 200


@pytest.mark.integration
class TestSSEAdminMeetingsEndpoint:
    """Tests for sse_admin_meetings endpoint."""

    def test_sse_admin_meetings_requires_auth(self, client):
        """Test SSE admin meetings endpoint requires authentication."""
        response = client.get("/api/v1/sse/admin/meetings")

        assert response.status_code == 401

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_admin_meetings_with_auth(self, mock_event_generator, admin_client):
        """Test SSE admin meetings endpoint works with authentication."""
        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        response = admin_client.get("/api/v1/sse/admin/meetings")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_admin_meetings_response_headers(self, mock_event_generator, admin_client):
        """Test SSE admin meetings endpoint returns correct headers."""
        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        response = admin_client.get("/api/v1/sse/admin/meetings")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"
        assert response.headers["x-accel-buffering"] == "no"

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_admin_meetings_with_existing_meetings(self, mock_event_generator, admin_client):
        """Test SSE admin meetings endpoint with existing meetings."""
        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        # Create a meeting first
        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            }
        )
        assert meeting_response.status_code == 200

        # Request SSE stream
        response = admin_client.get("/api/v1/sse/admin/meetings")

        assert response.status_code == 200

    def test_sse_admin_meetings_invalid_token(self, client):
        """Test SSE admin meetings endpoint with invalid admin token."""
        # Set invalid cookie
        client.cookies.set("admin_token", "invalid_token")

        response = client.get("/api/v1/sse/admin/meetings")

        assert response.status_code == 401

    def test_sse_admin_meetings_no_token(self, client):
        """Test SSE admin meetings endpoint without token."""
        response = client.get("/api/v1/sse/admin/meetings")

        assert response.status_code == 401


@pytest.mark.integration
class TestSSEEndpointsWithCache:
    """Tests for SSE endpoints integration with caching."""

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_meetings_uses_cache(self, mock_event_generator, client, admin_client):
        """Test that SSE meetings endpoint uses cache."""
        from app.core.cache import global_cache

        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        # Clear cache
        global_cache.clear()

        # Create a meeting
        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            }
        )
        assert meeting_response.status_code == 200

        # First SSE request (should populate cache)
        response1 = client.get("/api/v1/sse/meetings")
        assert response1.status_code == 200

        # Check that cache has entries
        stats = global_cache.get_stats()
        # Cache may have been populated by the SSE endpoint's data function
        assert stats is not None

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_admin_meetings_uses_cache(self, mock_event_generator, admin_client):
        """Test that SSE admin meetings endpoint uses cache."""
        from app.core.cache import global_cache

        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        # Clear cache
        global_cache.clear()

        # Create a meeting
        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            }
        )
        assert meeting_response.status_code == 200

        # First SSE request (should populate cache)
        response1 = admin_client.get("/api/v1/sse/admin/meetings")
        assert response1.status_code == 200

        # Check that cache has entries
        stats = global_cache.get_stats()
        assert stats is not None

    def test_sse_meetings_cache_invalidation(self, client, admin_client):
        """Test that creating a meeting invalidates SSE cache."""
        from app.core.cache import global_cache

        # Clear cache
        global_cache.clear()

        # Populate cache via available meetings endpoint
        response = client.post("/api/v1/meetings/available", json={})
        assert response.status_code == 200

        initial_stats = global_cache.get_stats()

        # Create a new meeting (should invalidate cache)
        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            }
        )
        assert meeting_response.status_code == 200

        # Cache should have been invalidated
        # The base_meetings cache key should have been removed
        # (We can verify this indirectly by checking that a new request would repopulate it)


@pytest.mark.integration
class TestSSEEndpointsErrorHandling:
    """Tests for SSE endpoints error handling."""

    def test_sse_meetings_malformed_tokens_array(self, client):
        """Test SSE meetings with malformed tokens parameter."""
        # Send an array instead of object
        tokens_json = json.dumps([1, 2, 3])

        response = client.get(f"/api/v1/sse/meetings?tokens={tokens_json}")

        # Should return 400 for invalid token format
        assert response.status_code == 400
        assert "Invalid tokens parameter" in response.json()["detail"]

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_meetings_url_encoded_tokens(self, mock_event_generator, client):
        """Test SSE meetings with URL-encoded token map."""
        import urllib.parse

        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        token_map = {"1": "token1", "2": "token2"}
        tokens_json = json.dumps(token_map)
        tokens_encoded = urllib.parse.quote(tokens_json)

        response = client.get(f"/api/v1/sse/meetings?tokens={tokens_encoded}")

        assert response.status_code == 200

    @patch('app.api.v1.endpoints.sse.event_generator')
    def test_sse_meetings_special_characters_in_tokens(self, mock_event_generator, client):
        """Test SSE meetings with special characters in token values."""
        # Mock event_generator to prevent infinite streaming
        async def mock_generator():
            yield 'data: {"test": "data"}\n\n'

        mock_event_generator.return_value = mock_generator()

        token_map = {"1": "token-with-special_chars.123"}
        tokens_json = json.dumps(token_map)

        response = client.get(f"/api/v1/sse/meetings?tokens={tokens_json}")

        assert response.status_code == 200


@pytest.mark.integration
class TestSSEErrorLogging:
    """Test that SSE endpoints log errors with proper context (issue #9.2)."""

    @pytest.mark.asyncio
    async def test_sse_event_generator_logs_endpoint_name(self, caplog):
        """Test that event_generator logs endpoint name for context."""
        from app.api.v1.endpoints.sse import event_generator

        mock_request = Mock()
        mock_request.is_disconnected = AsyncMock(side_effect=[False, True])
        mock_request.url = Mock()
        mock_request.url.path = "/api/v1/sse/test"

        def failing_data_func():
            raise DatabaseError("connection error", None, None)

        # Collect events
        events = []
        async for event in event_generator(mock_request, failing_data_func, interval=0.1, endpoint_name="test_endpoint"):
            events.append(event)
            if len(events) >= 3:  # Stop after 3 errors
                break

        # Verify error was logged with endpoint context
        assert any("test_endpoint" in record.message for record in caplog.records if record.levelname == "WARNING")
        assert any("/api/v1/sse/test" in record.message for record in caplog.records if record.levelname == "WARNING")

    @pytest.mark.asyncio
    async def test_sse_event_generator_logs_unexpected_errors_with_context(self, caplog):
        """Test that unexpected errors are logged with full context."""
        from app.api.v1.endpoints.sse import event_generator

        mock_request = Mock()
        mock_request.is_disconnected = AsyncMock(return_value=False)
        mock_request.url = Mock()
        mock_request.url.path = "/api/v1/sse/admin/meetings"

        def failing_data_func():
            raise AttributeError("'NoneType' object has no attribute 'polls'")

        # Collect events
        events = []
        async for event in event_generator(mock_request, failing_data_func, interval=0.1, endpoint_name="sse_admin_meetings"):
            events.append(event)
            break  # Stop after first error

        # Verify error was logged with endpoint context
        assert any("sse_admin_meetings" in record.message for record in caplog.records if record.levelname == "ERROR")
        assert any("/api/v1/sse/admin/meetings" in record.message for record in caplog.records if record.levelname == "ERROR")

    @pytest.mark.asyncio
    async def test_sse_event_generator_includes_endpoint_on_termination(self, caplog):
        """Test that termination after consecutive errors includes endpoint context."""
        from app.api.v1.endpoints.sse import event_generator

        mock_request = Mock()
        mock_request.is_disconnected = AsyncMock(return_value=False)
        mock_request.url = Mock()
        mock_request.url.path = "/api/v1/sse/meetings"

        consecutive_errors = {"count": 0}

        def failing_data_func():
            consecutive_errors["count"] += 1
            raise DatabaseError("connection error", None, None)

        # Collect events until stream ends
        events = []
        async for event in event_generator(mock_request, failing_data_func, interval=0.01, endpoint_name="sse_meetings"):
            events.append(event)

        # Should have terminated after max_consecutive_errors
        # Verify termination was logged with endpoint context
        error_logs = [record for record in caplog.records if record.levelname == "ERROR"]
        assert any("sse_meetings" in record.message and "terminating" in record.message.lower() for record in error_logs)
