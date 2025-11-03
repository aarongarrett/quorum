"""Unit tests for SSE event_generator function."""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock
from sqlalchemy.exc import SQLAlchemyError, DatabaseError

from app.api.v1.endpoints.sse import event_generator


@pytest.mark.unit
class TestEventGenerator:
    """Tests for event_generator async function."""

    @pytest.mark.asyncio
    async def test_event_generator_success(self):
        """Test event generator yields data successfully."""
        # Mock request that never disconnects
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        # Mock data function
        data_func = Mock(return_value={"test": "data"})

        # Create generator
        gen = event_generator(request, data_func, interval=0.01)

        # Get first event
        event = await gen.__anext__()

        # Verify event format
        assert event == 'data: {"test": "data"}\n\n'
        assert data_func.call_count == 1

        # Stop the generator
        await gen.aclose()

    @pytest.mark.asyncio
    async def test_event_generator_multiple_events(self):
        """Test event generator yields multiple events."""
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        call_count = {"count": 0}

        def data_func():
            call_count["count"] += 1
            return {"iteration": call_count["count"]}

        gen = event_generator(request, data_func, interval=0.01)

        # Get multiple events
        events = []
        i = 0
        async for event in gen:
            events.append(event)
            i += 1
            if i >= 3:  # Get 3 events
                break

        await gen.aclose()

        # Verify we got 3 events
        assert len(events) == 3
        assert events[0] == 'data: {"iteration": 1}\n\n'
        assert events[1] == 'data: {"iteration": 2}\n\n'
        assert events[2] == 'data: {"iteration": 3}\n\n'

    @pytest.mark.asyncio
    async def test_event_generator_client_disconnect(self):
        """Test event generator stops when client disconnects."""
        request = Mock()
        # Simulate client disconnect after first check
        disconnect_calls = {"count": 0}

        async def mock_is_disconnected():
            disconnect_calls["count"] += 1
            return disconnect_calls["count"] > 1  # Disconnect after first iteration

        request.is_disconnected = mock_is_disconnected

        data_func = Mock(return_value={"test": "data"})

        gen = event_generator(request, data_func, interval=0.01)

        # Collect all events
        events = []
        async for event in gen:
            events.append(event)

        # Should get at least one event before disconnect
        assert len(events) >= 1
        assert events[0] == 'data: {"test": "data"}\n\n'

    @pytest.mark.asyncio
    async def test_event_generator_database_error_retry(self):
        """Test event generator retries on database errors."""
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        call_count = {"count": 0}

        def data_func():
            call_count["count"] += 1
            if call_count["count"] <= 2:
                raise SQLAlchemyError("Database connection lost")
            return {"success": True}

        gen = event_generator(request, data_func, interval=0.01)

        # Get events
        events = []
        async for event in gen:
            events.append(event)
            if 'data:' in event:  # Get first successful event
                break

        await gen.aclose()

        # Should eventually succeed after retries
        assert len(events) >= 1
        assert 'data: {"success": true}' in events[-1]
        assert call_count["count"] == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_event_generator_max_database_errors(self):
        """Test event generator terminates after max consecutive database errors."""
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        def data_func():
            raise DatabaseError("statement", "params", "orig")

        gen = event_generator(request, data_func, interval=0.01)

        # Collect all events
        events = []
        async for event in gen:
            events.append(event)

        # Should get error event after 3 failures
        assert len(events) == 1
        assert "event: error" in events[0]
        assert "Service temporarily unavailable" in events[0]

    @pytest.mark.asyncio
    async def test_event_generator_unexpected_error(self):
        """Test event generator handles unexpected errors."""
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        def data_func():
            raise AttributeError("Unexpected error")

        gen = event_generator(request, data_func, interval=0.01)

        # Collect all events
        events = []
        async for event in gen:
            events.append(event)

        # Should get error event immediately
        assert len(events) == 1
        assert "event: error" in events[0]
        assert "Internal error" in events[0]

    @pytest.mark.asyncio
    async def test_event_generator_resets_error_counter_on_success(self):
        """Test that error counter resets after successful data fetch."""
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        call_count = {"count": 0}

        def data_func():
            call_count["count"] += 1
            # Fail on iterations 1 and 2, succeed on 3, fail on 4 and 5, succeed on 6
            if call_count["count"] in [1, 2, 4, 5]:
                raise SQLAlchemyError("Database error")
            return {"iteration": call_count["count"]}

        gen = event_generator(request, data_func, interval=0.01)

        # Collect events
        events = []
        data_event_count = 0
        async for event in gen:
            events.append(event)
            if event.startswith("data:"):
                data_event_count += 1
            if data_event_count >= 2:  # Get 2 successful events
                break

        await gen.aclose()

        # Should have 2 successful data events (iterations 3 and 6)
        data_events = [e for e in events if e.startswith("data:")]
        assert len(data_events) == 2
        assert 'data: {"iteration": 3}' in data_events[0]
        assert 'data: {"iteration": 6}' in data_events[1]

    @pytest.mark.asyncio
    async def test_event_generator_asyncio_cancelled(self):
        """Test event generator handles asyncio.CancelledError."""
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        data_func = Mock(return_value={"test": "data"})

        gen = event_generator(request, data_func, interval=0.01)

        # Get first event
        await gen.__anext__()

        # Simulate cancellation by throwing CancelledError into generator
        try:
            await gen.athrow(asyncio.CancelledError())
        except (StopAsyncIteration, asyncio.CancelledError):
            pass  # Expected

        # Generator should handle CancelledError gracefully

    @pytest.mark.asyncio
    async def test_event_generator_custom_interval(self):
        """Test event generator respects custom interval."""
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        data_func = Mock(return_value={"test": "data"})

        # Test with measurable interval
        gen = event_generator(request, data_func, interval=0.05)

        import time
        start_time = time.time()

        # Get 3 events to ensure we measure at least 2 intervals
        events = []
        i = 0
        async for event in gen:
            events.append(event)
            i += 1
            if i >= 3:
                break

        end_time = time.time()

        await gen.aclose()

        # Should have taken at least 2 intervals (0.1 seconds)
        # Use a slightly lower threshold to account for timing imprecision
        elapsed = end_time - start_time
        assert elapsed >= 0.08  # At least 2 intervals minus some tolerance
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_event_generator_json_serializable_data(self):
        """Test event generator properly serializes various data types."""
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        test_data = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": "value"}
        }

        data_func = Mock(return_value=test_data)

        gen = event_generator(request, data_func, interval=0.01)

        # Get first event
        event = await gen.__anext__()

        await gen.aclose()

        # Verify JSON serialization
        assert event.startswith("data: ")
        json_str = event.replace("data: ", "").strip()
        parsed_data = json.loads(json_str)
        assert parsed_data == test_data

    @pytest.mark.asyncio
    async def test_event_generator_consecutive_errors_count(self):
        """Test that consecutive errors are counted correctly."""
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        call_count = {"count": 0}

        def data_func():
            call_count["count"] += 1
            # Always raise database error
            raise SQLAlchemyError("Database error")

        gen = event_generator(request, data_func, interval=0.01)

        # Collect all events
        events = []
        async for event in gen:
            events.append(event)

        # Should call data_func 3 times (max_consecutive_errors), then yield error
        assert call_count["count"] == 3
        assert len(events) == 1
        assert "event: error" in events[0]
        assert "Service temporarily unavailable" in events[0]

    @pytest.mark.asyncio
    async def test_event_generator_different_error_types(self):
        """Test event generator distinguishes between error types."""
        request = Mock()
        request.is_disconnected = AsyncMock(return_value=False)

        # Test DatabaseError (should retry)
        def data_func_db_error():
            raise DatabaseError("statement", "params", "orig")

        gen = event_generator(request, data_func_db_error, interval=0.01)

        events_db = []
        async for event in gen:
            events_db.append(event)

        # Should retry and then error
        assert "Service temporarily unavailable" in events_db[0]

        # Test other exceptions (should fail immediately)
        request2 = Mock()
        request2.is_disconnected = AsyncMock(return_value=False)

        def data_func_other_error():
            raise ValueError("Some other error")

        gen2 = event_generator(request2, data_func_other_error, interval=0.01)

        events_other = []
        async for event in gen2:
            events_other.append(event)

        # Should fail immediately
        assert len(events_other) == 1
        assert "Internal error" in events_other[0]
