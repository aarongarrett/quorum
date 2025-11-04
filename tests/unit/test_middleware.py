"""Unit tests for middleware."""
import pytest
from unittest.mock import Mock, AsyncMock
from app.middleware.logging import LoggingMiddleware


@pytest.mark.unit
class TestLoggingMiddleware:
    """Test logging middleware."""

    @pytest.mark.asyncio
    async def test_request_id_added_to_state(self):
        """Test that request ID is added to request.state (issue #11.1)."""
        # Create mock request and response
        mock_request = Mock()
        mock_request.state = Mock()
        mock_request.method = "GET"
        mock_request.url = Mock()
        mock_request.url.path = "/test"
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.query_params = {}

        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 200

        # Create mock call_next
        async def mock_call_next(request):
            # Verify request_id is set in request.state before processing
            assert hasattr(request.state, 'request_id')
            assert isinstance(request.state.request_id, str)
            assert len(request.state.request_id) > 0
            return mock_response

        # Create middleware
        app = Mock()
        middleware = LoggingMiddleware(app)

        # Call middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify request_id was added to request.state
        assert hasattr(mock_request.state, 'request_id')
        assert isinstance(mock_request.state.request_id, str)
        assert len(mock_request.state.request_id) > 0

        # Verify request_id was added to response headers
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] == mock_request.state.request_id

    @pytest.mark.asyncio
    async def test_request_id_added_to_response_headers(self):
        """Test that X-Request-ID header is added to response (issue #11.1)."""
        # Create mock request and response
        mock_request = Mock()
        mock_request.state = Mock()
        mock_request.method = "POST"
        mock_request.url = Mock()
        mock_request.url.path = "/api/v1/test"
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"
        mock_request.query_params = {"key": "value"}

        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 201

        # Create mock call_next
        async def mock_call_next(request):
            return mock_response

        # Create middleware
        app = Mock()
        middleware = LoggingMiddleware(app)

        # Call middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify X-Request-ID header is present
        assert "X-Request-ID" in response.headers
        assert isinstance(response.headers["X-Request-ID"], str)
        assert len(response.headers["X-Request-ID"]) > 0

    @pytest.mark.asyncio
    async def test_request_id_consistent_between_state_and_header(self):
        """Test that request.state.request_id matches X-Request-ID header."""
        # Create mock request and response
        mock_request = Mock()
        mock_request.state = Mock()
        mock_request.method = "GET"
        mock_request.url = Mock()
        mock_request.url.path = "/health"
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.query_params = {}

        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 200

        # Create mock call_next
        async def mock_call_next(request):
            return mock_response

        # Create middleware
        app = Mock()
        middleware = LoggingMiddleware(app)

        # Call middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify request_id in state matches header
        assert mock_request.state.request_id == response.headers["X-Request-ID"]

    @pytest.mark.asyncio
    async def test_request_id_unique_across_requests(self):
        """Test that each request gets a unique request ID."""
        # Create first request
        mock_request1 = Mock()
        mock_request1.state = Mock()
        mock_request1.method = "GET"
        mock_request1.url = Mock()
        mock_request1.url.path = "/test1"
        mock_request1.client = Mock()
        mock_request1.client.host = "127.0.0.1"
        mock_request1.query_params = {}

        mock_response1 = Mock()
        mock_response1.headers = {}
        mock_response1.status_code = 200

        # Create second request
        mock_request2 = Mock()
        mock_request2.state = Mock()
        mock_request2.method = "GET"
        mock_request2.url = Mock()
        mock_request2.url.path = "/test2"
        mock_request2.client = Mock()
        mock_request2.client.host = "127.0.0.1"
        mock_request2.query_params = {}

        mock_response2 = Mock()
        mock_response2.headers = {}
        mock_response2.status_code = 200

        # Create mock call_next
        async def mock_call_next1(request):
            return mock_response1

        async def mock_call_next2(request):
            return mock_response2

        # Create middleware
        app = Mock()
        middleware = LoggingMiddleware(app)

        # Call middleware for both requests
        response1 = await middleware.dispatch(mock_request1, mock_call_next1)
        response2 = await middleware.dispatch(mock_request2, mock_call_next2)

        # Verify each request has a unique request ID
        request_id1 = response1.headers["X-Request-ID"]
        request_id2 = response2.headers["X-Request-ID"]

        assert request_id1 != request_id2
        assert mock_request1.state.request_id != mock_request2.state.request_id
