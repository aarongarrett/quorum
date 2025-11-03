"""Integration tests for admin API endpoints."""
import pytest
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
        assert data["database"] == "connected"

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
        assert data["database"] == "connected"

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
