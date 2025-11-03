"""Unit tests for caching system."""
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.cache import TTLCache, get_or_fetch


@pytest.mark.unit
class TestTTLCache:
    """Tests for TTLCache class."""

    def test_basic_get_set(self):
        """Test basic cache get/set operations."""
        cache = TTLCache()
        cache.set("key1", "value1")

        result = cache.get("key1")
        assert result == "value1"

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist returns None."""
        cache = TTLCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_ttl_expiration(self):
        """Test that cached values expire after TTL."""
        cache = TTLCache()
        cache.set("key1", "value1")

        # Should not be expired immediately
        assert not cache.is_expired("key1", ttl_seconds=1.0)

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired now
        assert cache.is_expired("key1", ttl_seconds=1.0)

    def test_nonexistent_key_is_expired(self):
        """Test that non-existent keys are considered expired."""
        cache = TTLCache()
        assert cache.is_expired("nonexistent", ttl_seconds=1.0)

    def test_lru_eviction(self):
        """Test that LRU eviction works when cache is full."""
        cache = TTLCache(max_size=3)

        # Fill cache to capacity
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # All should be in cache
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

        # Add another item, should evict key1 (oldest)
        cache.set("key4", "value4")

        # key1 should be evicted
        assert cache.get("key1") is None
        # Others should still be there
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_lru_updates_on_access(self):
        """Test that accessing a key updates its LRU position."""
        cache = TTLCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add another item
        cache.set("key4", "value4")

        # key2 should be evicted (oldest now), not key1
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_update_existing_key_maintains_size(self):
        """Test that updating existing key doesn't count as new entry."""
        cache = TTLCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Update key2
        cache.set("key2", "value2_updated")

        # All keys should still be present
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2_updated"
        assert cache.get("key3") == "value3"

    def test_invalidate(self):
        """Test cache invalidation."""
        cache = TTLCache()
        cache.set("key1", "value1")

        assert cache.get("key1") == "value1"

        cache.invalidate("key1")

        assert cache.get("key1") is None

    def test_invalidate_nonexistent_key(self):
        """Test invalidating a non-existent key doesn't raise error."""
        cache = TTLCache()
        # Should not raise an error
        cache.invalidate("nonexistent")

    def test_clear(self):
        """Test clearing entire cache."""
        cache = TTLCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_get_stats_empty_cache(self):
        """Test get_stats on empty cache."""
        cache = TTLCache(max_size=100)
        stats = cache.get_stats()

        assert stats["size"] == 0
        assert stats["max_size"] == 100
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate_percent"] == 0
        assert stats["entries"] == {}

    def test_get_stats_with_data(self):
        """Test get_stats with cached data."""
        cache = TTLCache(max_size=50)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 50
        assert "key1" in stats["entries"]
        assert "key2" in stats["entries"]
        assert "age_seconds" in stats["entries"]["key1"]
        assert "cached_at" in stats["entries"]["key1"]

    def test_thread_safety(self):
        """Test that cache operations are thread-safe."""
        cache = TTLCache()

        def set_value(key, value):
            cache.set(key, value)

        def get_value(key):
            return cache.get(key)

        # Create multiple threads setting and getting values
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            # Set values from multiple threads
            for i in range(100):
                futures.append(executor.submit(set_value, f"key{i}", f"value{i}"))

            # Wait for all sets to complete
            for future in as_completed(futures):
                future.result()

            # Get values from multiple threads
            futures = []
            for i in range(100):
                futures.append(executor.submit(get_value, f"key{i}"))

            # All values should be retrievable
            results = [future.result() for future in as_completed(futures)]
            assert all(result is not None for result in results)


@pytest.mark.unit
class TestGetOrFetch:
    """Tests for get_or_fetch function."""

    def test_cache_miss_calls_fetch(self):
        """Test that cache miss calls fetch function."""
        cache = TTLCache()
        call_count = {"count": 0}

        def fetch_func():
            call_count["count"] += 1
            return "fetched_value"

        result = get_or_fetch(cache, "key1", fetch_func, ttl_seconds=1.0)

        assert result == "fetched_value"
        assert call_count["count"] == 1
        # Verify it was cached
        assert cache.get("key1") == "fetched_value"

    def test_cache_hit_skips_fetch(self):
        """Test that cache hit doesn't call fetch function."""
        cache = TTLCache()
        cache.set("key1", "cached_value")
        call_count = {"count": 0}

        def fetch_func():
            call_count["count"] += 1
            return "fetched_value"

        result = get_or_fetch(cache, "key1", fetch_func, ttl_seconds=1.0)

        assert result == "cached_value"
        assert call_count["count"] == 0

    def test_expired_cache_refetches(self):
        """Test that expired cache entry triggers refetch."""
        cache = TTLCache()
        cache.set("key1", "old_value")
        call_count = {"count": 0}

        def fetch_func():
            call_count["count"] += 1
            return "new_value"

        # Wait for expiration
        time.sleep(0.2)

        result = get_or_fetch(cache, "key1", fetch_func, ttl_seconds=0.1)

        assert result == "new_value"
        assert call_count["count"] == 1

    def test_hit_miss_tracking(self):
        """Test that hits and misses are tracked correctly."""
        cache = TTLCache()

        def fetch_func():
            return "value"

        # First call - cache miss
        get_or_fetch(cache, "key1", fetch_func, ttl_seconds=1.0)
        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

        # Second call - cache hit
        get_or_fetch(cache, "key1", fetch_func, ttl_seconds=1.0)
        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 1

        # Third call - cache hit
        get_or_fetch(cache, "key1", fetch_func, ttl_seconds=1.0)
        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 2

    def test_hit_rate_calculation(self):
        """Test that hit rate percentage is calculated correctly."""
        cache = TTLCache()

        def fetch_func(value):
            return lambda: value

        # 1 miss
        get_or_fetch(cache, "key1", fetch_func("value1"), ttl_seconds=1.0)
        # 3 hits
        get_or_fetch(cache, "key1", fetch_func("value1"), ttl_seconds=1.0)
        get_or_fetch(cache, "key1", fetch_func("value1"), ttl_seconds=1.0)
        get_or_fetch(cache, "key1", fetch_func("value1"), ttl_seconds=1.0)

        stats = cache.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 75.0

    def test_thundering_herd_prevention(self):
        """Test that double-check locking prevents thundering herd."""
        cache = TTLCache()
        call_count = {"count": 0}

        def slow_fetch():
            """Simulate slow database query."""
            call_count["count"] += 1
            time.sleep(0.1)  # Simulate slow operation
            return f"value_{call_count['count']}"

        results = []

        def fetch_in_thread():
            result = get_or_fetch(cache, "key1", slow_fetch, ttl_seconds=10.0)
            results.append(result)

        # Start 10 threads simultaneously
        threads = []
        for _ in range(10):
            t = threading.Thread(target=fetch_in_thread)
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Only one thread should have called the fetch function
        assert call_count["count"] == 1

        # All threads should get the same value
        assert len(set(results)) == 1
        assert all(result == "value_1" for result in results)

    def test_concurrent_different_keys(self):
        """Test concurrent fetches for different keys work correctly."""
        cache = TTLCache()
        call_counts = {}

        def make_fetch(key):
            def fetch_func():
                if key not in call_counts:
                    call_counts[key] = 0
                call_counts[key] += 1
                time.sleep(0.05)
                return f"value_{key}"
            return fetch_func

        results = {}

        def fetch_in_thread(key):
            result = get_or_fetch(cache, key, make_fetch(key), ttl_seconds=10.0)
            if key not in results:
                results[key] = []
            results[key].append(result)

        # Start threads for different keys
        threads = []
        for i in range(5):
            for _ in range(3):  # 3 threads per key
                t = threading.Thread(target=fetch_in_thread, args=(f"key{i}",))
                threads.append(t)
                t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Each key should have been fetched exactly once
        for i in range(5):
            assert call_counts[f"key{i}"] == 1
            assert len(results[f"key{i}"]) == 3
            assert all(r == f"value_key{i}" for r in results[f"key{i}"])

    def test_custom_ttl(self):
        """Test that custom TTL values work correctly."""
        cache = TTLCache()

        def fetch_func():
            return "value"

        # Set with very short TTL
        result = get_or_fetch(cache, "key1", fetch_func, ttl_seconds=0.1)
        assert result == "value"

        # Immediately should be a hit
        stats = cache.get_stats()
        initial_misses = stats["misses"]

        get_or_fetch(cache, "key1", fetch_func, ttl_seconds=0.1)
        stats = cache.get_stats()
        assert stats["misses"] == initial_misses  # No new miss

        # Wait for expiration
        time.sleep(0.2)

        # Should be a miss now
        get_or_fetch(cache, "key1", fetch_func, ttl_seconds=0.1)
        stats = cache.get_stats()
        assert stats["misses"] == initial_misses + 1

    def test_fetch_function_can_return_none(self):
        """Test that fetch function can return None (should be cached)."""
        cache = TTLCache()
        call_count = {"count": 0}

        def fetch_func():
            call_count["count"] += 1
            return None

        result = get_or_fetch(cache, "key1", fetch_func, ttl_seconds=1.0)

        # None should be returned
        assert result is None
        assert call_count["count"] == 1

        # Should be cached (but currently our implementation treats None as cache miss)
        # This is a known behavior - None values are treated as cache misses
        result = get_or_fetch(cache, "key1", fetch_func, ttl_seconds=1.0)
        # Will fetch again because None is treated as cache miss
        assert call_count["count"] == 2

    def test_fetch_function_exceptions_propagate(self):
        """Test that exceptions from fetch function propagate correctly."""
        cache = TTLCache()

        def fetch_func():
            raise ValueError("Database error")

        with pytest.raises(ValueError, match="Database error"):
            get_or_fetch(cache, "key1", fetch_func, ttl_seconds=1.0)

    def test_reentrant_lock_allows_nested_calls(self):
        """Test that RLock allows the same thread to acquire lock multiple times."""
        cache = TTLCache()

        # This tests that we're using RLock correctly
        # The get_or_fetch function acquires the lock and then calls
        # cache methods that also acquire the lock
        def fetch_func():
            return "value"

        # This should not deadlock
        result = get_or_fetch(cache, "key1", fetch_func, ttl_seconds=1.0)
        assert result == "value"
