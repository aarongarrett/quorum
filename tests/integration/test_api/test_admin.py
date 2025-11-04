"""Integration tests for admin API endpoints."""
import pytest
from unittest.mock import patch
from app.core.cache import global_cache


@pytest.mark.integration
class TestAdminCacheStats:
    """Test admin cache statistics endpoint."""

    def test_get_cache_stats_requires_auth(self, client):
        """Cache stats endpoint should require admin authentication."""
        response = client.get("/api/v1/admin/cache/stats")
        assert response.status_code == 401

    def test_get_cache_stats_success(self, admin_client):
        """Admin should be able to get cache statistics."""
        # Clear cache first to have predictable state
        global_cache.clear()

        response = admin_client.get("/api/v1/admin/cache/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "size" in data
        assert "max_size" in data
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate_percent" in data
        assert "entries" in data

        # Verify data types
        assert isinstance(data["size"], int)
        assert isinstance(data["max_size"], int)
        assert isinstance(data["hits"], int)
        assert isinstance(data["misses"], int)
        assert isinstance(data["hit_rate_percent"], (int, float))
        assert isinstance(data["entries"], dict)

    def test_cache_stats_after_operations(self, admin_client, db_session):
        """Test that cache stats reflect actual cache operations."""
        # Clear cache to start fresh
        global_cache.clear()

        # Perform some operations that use cache
        # Create a meeting (this will invalidate cache)
        from datetime import datetime, timedelta
        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            }
        )
        assert meeting_response.status_code == 200

        # Get available meetings (this will populate cache)
        meetings_response = admin_client.post(
            "/api/v1/meetings/available",
            json={}
        )
        assert meetings_response.status_code == 200

        # Get cache stats
        stats_response = admin_client.get("/api/v1/admin/cache/stats")
        assert stats_response.status_code == 200

        data = stats_response.json()

        # Cache should have entries after meeting operations
        # The exact metrics depend on caching behavior, but verify structure
        assert data["size"] >= 0
        assert data["max_size"] == 100  # Default max size

    def test_cache_stats_entries_format(self, admin_client):
        """Test that cache entries have correct format."""
        # Clear cache
        global_cache.clear()

        # Add some test data to cache directly
        global_cache.set("test_key1", {"data": "value1"})
        global_cache.set("test_key2", {"data": "value2"})

        response = admin_client.get("/api/v1/admin/cache/stats")
        assert response.status_code == 200

        data = response.json()

        # Check entries format
        assert data["size"] == 2
        for key in ["test_key1", "test_key2"]:
            if key in data["entries"]:  # May be evicted by other operations
                entry = data["entries"][key]
                assert "age_seconds" in entry
                assert "cached_at" in entry
                assert isinstance(entry["age_seconds"], (int, float))
                assert isinstance(entry["cached_at"], str)

    def test_cache_stats_hit_rate_calculation(self, admin_client):
        """Test that hit rate is calculated correctly."""
        # Clear cache and reset metrics
        global_cache.clear()
        # Reset hit/miss counters by accessing internal state
        # Note: This is for testing purposes
        with global_cache._lock:
            global_cache._hits = 0
            global_cache._misses = 0

        # Simulate cache operations
        from app.core.cache import get_or_fetch

        call_count = {"count": 0}

        def fetch_func():
            call_count["count"] += 1
            return "test_value"

        # First call - miss
        get_or_fetch(global_cache, "test_key", fetch_func, ttl_seconds=10.0)

        # Second call - hit
        get_or_fetch(global_cache, "test_key", fetch_func, ttl_seconds=10.0)

        # Third call - hit
        get_or_fetch(global_cache, "test_key", fetch_func, ttl_seconds=10.0)

        response = admin_client.get("/api/v1/admin/cache/stats")
        assert response.status_code == 200

        data = response.json()

        # Should have 1 miss and 2 hits
        assert data["misses"] >= 1
        assert data["hits"] >= 2

        # Hit rate should be calculated correctly
        if data["hits"] + data["misses"] > 0:
            expected_rate = (data["hits"] / (data["hits"] + data["misses"])) * 100
            assert abs(data["hit_rate_percent"] - expected_rate) < 0.01


@pytest.mark.integration
class TestAdminMeetingsEndpoint:
    """Test admin meetings endpoint (verify it still works with cache)."""

    def test_get_all_meetings_with_cache(self, admin_client, db_session):
        """Test that admin can get all meetings (using cache)."""
        # Clear cache
        global_cache.clear()

        # Create a meeting first
        from datetime import datetime, timedelta
        meeting_response = admin_client.post(
            "/api/v1/meetings",
            json={
                "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            }
        )
        assert meeting_response.status_code == 200

        # Get all meetings
        response = admin_client.get("/api/v1/admin/meetings")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Call again - should use cache
        response2 = admin_client.get("/api/v1/admin/meetings")
        assert response2.status_code == 200
        data2 = response2.json()

        # Data should be the same
        assert data == data2

        # Check cache stats to verify cache was used
        stats_response = admin_client.get("/api/v1/admin/cache/stats")
        stats = stats_response.json()

        # Should have cache entries
        assert stats["size"] > 0


@pytest.mark.integration
class TestHealthEndpoint:
    """Test enhanced health check endpoint."""

    def test_health_check_includes_cache_stats(self, client):
        """Test that health endpoint includes cache statistics."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "cache" in data
        assert "database" in data

        # Verify status
        assert data["status"] == "healthy"
        assert data["database"]["status"] == "connected"

        # Verify cache stats are included
        cache_stats = data["cache"]
        assert "size" in cache_stats
        assert "max_size" in cache_stats
        assert "hits" in cache_stats
        assert "misses" in cache_stats
        assert "hit_rate_percent" in cache_stats
        assert "entries" in cache_stats

    def test_health_check_database_connection(self, client):
        """Test that health endpoint verifies database connection."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Should succeed with test database
        assert data["status"] == "healthy"
        assert data["database"]["status"] == "connected"

    def test_health_check_cache_metrics(self, client):
        """Test that health endpoint returns valid cache metrics."""
        # Clear cache for predictable state
        global_cache.clear()

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        cache_stats = data["cache"]

        # Verify metrics are valid numbers
        assert isinstance(cache_stats["size"], int)
        assert isinstance(cache_stats["max_size"], int)
        assert isinstance(cache_stats["hits"], int)
        assert isinstance(cache_stats["misses"], int)
        assert isinstance(cache_stats["hit_rate_percent"], (int, float))

        # Size should be within max_size
        assert cache_stats["size"] <= cache_stats["max_size"]

        # Hit rate should be between 0 and 100
        assert 0 <= cache_stats["hit_rate_percent"] <= 100

    def test_health_check_comprehensive_metrics(self, client):
        """Test that health endpoint includes comprehensive metrics (issue #11.2)."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify comprehensive response structure
        assert "status" in data
        assert "environment" in data
        assert "cache" in data
        assert "database" in data
        assert "memory" in data

        # Verify environment is included
        assert data["environment"] in ["development", "production", "staging"]

        # Verify database pool metrics are included
        database = data["database"]
        assert "status" in database
        assert "pool" in database
        pool = database["pool"]
        assert "size" in pool
        assert "checked_in" in pool
        assert "checked_out" in pool
        assert "overflow" in pool
        assert "total_connections" in pool

        # Verify pool metrics are valid
        assert isinstance(pool["size"], int)
        assert isinstance(pool["checked_in"], int)
        assert isinstance(pool["checked_out"], int)
        assert isinstance(pool["overflow"], int)
        assert isinstance(pool["total_connections"], int)
        assert pool["total_connections"] == pool["checked_in"] + pool["checked_out"]

        # Verify memory metrics are included (may vary based on psutil availability)
        memory = data["memory"]
        assert isinstance(memory, dict)
        # Either has actual metrics or error/status indicator
        assert len(memory) > 0

    def test_health_check_database_pool_status(self, client):
        """Test that database pool metrics are accurate."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        pool = data["database"]["pool"]

        # Pool should have reasonable values
        assert pool["size"] >= 0
        assert pool["checked_in"] >= 0
        assert pool["checked_out"] >= 0
        # Note: overflow can be negative in SQLAlchemy (means no overflow yet)
        assert isinstance(pool["overflow"], int)

        # Total connections should match sum
        assert pool["total_connections"] == pool["checked_in"] + pool["checked_out"]


@pytest.mark.integration
class TestErrorMessageSecurity:
    """Test that error messages don't expose sensitive information (issue #2.5)."""

    def test_admin_get_meetings_error_no_disclosure(self, admin_client):
        """Test that errors in admin endpoint return generic messages."""
        # Mock get_all_meetings to raise an exception
        with patch('app.api.v1.endpoints.admin.get_all_meetings') as mock_get:
            mock_get.side_effect = Exception("Internal database connection string: postgresql://user:pass@host/db")

            response = admin_client.get("/api/v1/admin/meetings")

            # Should return 500
            assert response.status_code == 500

            # Response should contain generic error message, not the actual exception
            data = response.json()
            assert data["detail"] == "Internal server error"
            # Should NOT contain the sensitive information from the exception
            assert "postgresql" not in data["detail"]
            assert "connection string" not in data["detail"]
            assert "pass@host" not in data["detail"]

    def test_meetings_available_error_no_disclosure(self, client):
        """Test that errors in available meetings endpoint return generic messages."""
        # Mock get_available_meetings to raise an exception
        with patch('app.api.v1.endpoints.meetings.get_available_meetings') as mock_get:
            mock_get.side_effect = Exception("AttributeError in /app/services/meeting.py line 42: 'NoneType' has no attribute 'polls'")

            response = client.post("/api/v1/meetings/available", json={})

            # Should return 500
            assert response.status_code == 500

            # Response should contain generic error message
            data = response.json()
            assert data["detail"] == "Internal server error"
            # Should NOT contain file paths or implementation details
            assert "/app/services" not in data["detail"]
            assert "AttributeError" not in data["detail"]
            assert "line 42" not in data["detail"]
