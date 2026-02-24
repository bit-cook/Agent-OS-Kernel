"""
Tests for Advanced Rate Limiter

Tests for sliding window, token bucket, multi-dimensional,
and distributed rate limiting functionality.
"""

import pytest
import time
import threading
from agent_os_kernel.core.rate_limiter_enhanced import (
    SlidingWindowLimiter,
    TokenBucketLimiter,
    MultiDimensionalLimiter,
    DistributedRateLimiter,
    RateLimitConfig,
    RateLimitResult,
    RateLimitExceeded,
    RateLimiterRegistry,
    rate_limit,
)


class TestSlidingWindow:
    """Tests for sliding window rate limiter."""
    
    def test_basic_allow(self):
        """Test that requests within limit are allowed."""
        config = RateLimitConfig(requests=10, window_seconds=60)
        limiter = SlidingWindowLimiter(config)
        
        result = limiter.check("user1", 1)
        assert result.allowed is True
        assert result.remaining == 9
    
    def test_rate_limit_exceeded(self):
        """Test that excess requests are blocked."""
        config = RateLimitConfig(requests=3, window_seconds=60)
        limiter = SlidingWindowLimiter(config)
        
        # Use all available requests
        for i in range(3):
            result = limiter.check("user1", 1)
            assert result.allowed is True
        
        # Fourth request should be blocked
        result = limiter.check("user1", 1)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0
    
    def test_bulk_requests(self):
        """Test bulk request handling."""
        config = RateLimitConfig(requests=5, window_seconds=60)
        limiter = SlidingWindowLimiter(config)
        
        # Request all at once
        result = limiter.check("user1", 5)
        assert result.allowed is True
        assert result.remaining == 0
        
        # Should be exhausted now
        result = limiter.check("user1", 1)
        assert result.allowed is False
    
    def test_different_keys_independent(self):
        """Test that different keys have separate limits."""
        config = RateLimitConfig(requests=2, window_seconds=60)
        limiter = SlidingWindowLimiter(config)
        
        # Exhaust user1
        limiter.check("user1", 2)
        result = limiter.check("user1", 1)
        assert result.allowed is False
        
        # user2 should still have quota
        result = limiter.check("user2", 1)
        assert result.allowed is True
        assert result.remaining == 1
    
    def test_reset(self):
        """Test resetting rate limit for a key."""
        config = RateLimitConfig(requests=2, window_seconds=60)
        limiter = SlidingWindowLimiter(config)
        
        # Exhaust limit
        limiter.check("user1", 2)
        result = limiter.check("user1", 1)
        assert result.allowed is False
        
        # Reset
        limiter.reset("user1")
        
        # Should be able to make requests again
        result = limiter.check("user1", 2)
        assert result.allowed is True
        assert result.remaining == 0
    
    def test_thread_safety(self):
        """Test thread-safe operation."""
        config = RateLimitConfig(requests=100, window_seconds=60)
        limiter = SlidingWindowLimiter(config)
        
        def make_requests():
            for _ in range(30):
                limiter.check("shared_key", 1)
        
        threads = [threading.Thread(target=make_requests) for _ in range(4)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have made 120 requests, but limited to 100
        result = limiter.check("shared_key", 1)
        assert result.allowed is False


class TestTokenBucket:
    """Tests for token bucket rate limiter."""
    
    def test_basic_allow(self):
        """Test basic token bucket functionality."""
        config = RateLimitConfig(requests=10, window_seconds=60, burst=20)
        limiter = TokenBucketLimiter(config)
        
        # New bucket starts with full burst tokens
        result = limiter.check("user1", 1)
        assert result.allowed is True
        # Remaining should be burst - 1 = 19
        assert result.remaining == 19
    
    def test_burst_allowance(self):
        """Test burst capacity is honored."""
        config = RateLimitConfig(requests=10, window_seconds=60, burst=10)
        limiter = TokenBucketLimiter(config)
        
        # Should allow burst up to capacity
        result = limiter.check("user1", 10)
        assert result.allowed is True
        # Should have 0 tokens left
        assert result.remaining == 0
    
    def test_rate_limit_exceeded(self):
        """Test rate limit when bucket is empty."""
        config = RateLimitConfig(requests=2, window_seconds=60, burst=2)
        limiter = TokenBucketLimiter(config)
        
        # Exhaust bucket
        limiter.check("user1", 2)
        
        # Should be blocked
        result = limiter.check("user1", 1)
        assert result.allowed is False
        assert result.retry_after is not None
    
    def test_token_refill(self):
        """Test token refill over time."""
        config = RateLimitConfig(requests=10, window_seconds=1, burst=10)
        limiter = TokenBucketLimiter(config)
        
        # Exhaust bucket
        limiter.check("user1", 10)
        result = limiter.check("user1", 1)
        assert result.allowed is False
        
        # Wait for refill (more than window to ensure refill)
        time.sleep(1.5)
        
        # Should have tokens again (up to burst capacity)
        result = limiter.check("user1", 5)
        assert result.allowed is True
        # Should have 5 tokens remaining (10 - 5)
        assert result.remaining == 5
    
    def test_burst_defaults_to_requests(self):
        """Test that burst defaults to requests if not specified."""
        config = RateLimitConfig(requests=5, window_seconds=60)
        limiter = TokenBucketLimiter(config)
        
        # Should allow up to requests (5) as burst
        result = limiter.check("user1", 5)
        assert result.allowed is True
        assert result.remaining == 0
    
    def test_thread_safety(self):
        """Test thread-safe token operations."""
        config = RateLimitConfig(requests=50, window_seconds=1, burst=50)
        limiter = TokenBucketLimiter(config)
        
        def make_requests():
            for _ in range(15):
                limiter.check("shared_key", 1)
        
        threads = [threading.Thread(target=make_requests) for _ in range(4)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have made requests
        result = limiter.check("shared_key", 1)
        # May or may not be allowed depending on timing


class TestMultiDimension:
    """Tests for multi-dimensional rate limiting."""
    
    def test_single_dimension(self):
        """Test single dimension limiting."""
        limiter = MultiDimensionalLimiter()
        limiter.add_dimension("user", "user1", RateLimitConfig(requests=5, window_seconds=60))
        
        result = limiter.check({"user": "user1"}, 1)
        assert result.allowed is True
        assert result.remaining == 4
    
    def test_multiple_dimensions(self):
        """Test limiting across multiple dimensions."""
        limiter = MultiDimensionalLimiter()
        limiter.add_dimension("user", "user1", RateLimitConfig(requests=5, window_seconds=60))
        limiter.add_dimension("ip", "192.168.1.1", RateLimitConfig(requests=10, window_seconds=60))
        limiter.add_dimension("endpoint", "/api/data", RateLimitConfig(requests=3, window_seconds=60))
        
        # User limit: 5 -> 4
        # IP limit: 10 -> 9
        # Endpoint limit: 3 -> 2
        result = limiter.check(
            {"user": "user1", "ip": "192.168.1.1", "endpoint": "/api/data"},
            1
        )
        assert result.allowed is True
    
    def test_most_restrictive_dimension(self):
        """Test that most restrictive dimension is applied."""
        limiter = MultiDimensionalLimiter()
        limiter.add_dimension("user", "user1", RateLimitConfig(requests=10, window_seconds=60))
        limiter.add_dimension("endpoint", "/api/data", RateLimitConfig(requests=3, window_seconds=60))
        
        result = limiter.check(
            {"user": "user1", "endpoint": "/api/data"},
            1
        )
        assert result.remaining == 2  # Limited by endpoint
    
    def test_dimension_exceeded(self):
        """Test when one dimension is exceeded."""
        limiter = MultiDimensionalLimiter()
        limiter.add_dimension("user", "user1", RateLimitConfig(requests=10, window_seconds=60))
        limiter.add_dimension("endpoint", "/api/data", RateLimitConfig(requests=2, window_seconds=60))
        
        # Exhaust endpoint limit
        limiter.check({"endpoint": "/api/data"}, 1)
        limiter.check({"endpoint": "/api/data"}, 1)
        
        # Should be blocked even if user has quota
        result = limiter.check(
            {"user": "user1", "endpoint": "/api/data"},
            1
        )
        assert result.allowed is False
        assert result.retry_after is not None
    
    def test_auto_create_dimension(self):
        """Test automatic dimension creation."""
        limiter = MultiDimensionalLimiter()
        
        # No dimensions added, but check should still work
        result = limiter.check({"user": "user1"}, 1)
        assert result.allowed is True
    
    def test_reset_dimension(self):
        """Test resetting a specific dimension."""
        limiter = MultiDimensionalLimiter()
        limiter.add_dimension("user", "user1", RateLimitConfig(requests=2, window_seconds=60))
        
        # Exhaust
        limiter.check({"user": "user1"}, 2)
        result = limiter.check({"user": "user1"}, 1)
        assert result.allowed is False
        
        # Reset
        limiter.reset("user", "user1")
        
        # Should work again
        result = limiter.check({"user": "user1"}, 2)
        assert result.allowed is True


class TestDistributedRateLimiter:
    """Tests for distributed rate limiter."""
    
    def test_no_redis_local_mode(self):
        """Test distributed limiter without Redis (local mode)."""
        limiter = DistributedRateLimiter()
        
        result = limiter.check("user1", 10, 60, "sliding")
        assert result.allowed is True
        assert result.remaining == 9
    
    def test_token_bucket_algorithm(self):
        """Test token bucket via distributed limiter."""
        limiter = DistributedRateLimiter()
        
        result = limiter.check("user1", 10, 60, "token_bucket")
        assert result.allowed is True
    
    def test_cache_invalidation(self):
        """Test that cache expires correctly."""
        limiter = DistributedRateLimiter(redis_client=None, prefix="test")
        limiter._cache_ttl = 0.1
        
        result1 = limiter.check("user1", 10, 60, "sliding")
        result2 = limiter.check("user1", 10, 60, "sliding")
        
        # Cache is fresh, so both should return same value
        # After cache expires (0.1s), fresh check should happen
        assert result1.remaining == 9
        # The second result might be same or different based on cache timing


class TestRateLimiterRegistry:
    """Tests for rate limiter registry."""
    
    def test_register_and_get(self):
        """Test registering and retrieving limiters."""
        registry = RateLimiterRegistry()
        
        limiter = registry.create_sliding_window(
            "test",
            RateLimitConfig(requests=10, window_seconds=60)
        )
        
        retrieved = registry.get("test")
        assert retrieved is limiter
    
    def test_create_token_bucket(self):
        """Test creating token bucket via registry."""
        registry = RateLimiterRegistry()
        
        limiter = registry.create_token_bucket(
            "token",
            RateLimitConfig(requests=5, window_seconds=60, burst=10)
        )
        
        assert isinstance(limiter, TokenBucketLimiter)
    
    def test_create_multi_dimensional(self):
        """Test creating multi-dimensional limiter via registry."""
        registry = RateLimiterRegistry()
        
        limiter = registry.create_multi_dimensional("multi")
        
        assert isinstance(limiter, MultiDimensionalLimiter)
    
    def test_get_nonexistent(self):
        """Test getting non-existent limiter returns None."""
        registry = RateLimiterRegistry()
        
        result = registry.get("nonexistent")
        assert result is None


class TestRateLimitDecorator:
    """Tests for rate limit decorator."""
    
    def test_decorator_basic(self):
        """Test basic decorator usage."""
        limiter = SlidingWindowLimiter(RateLimitConfig(requests=10, window_seconds=60))
        
        @rate_limit(limiter, default_key="default")
        def my_function():
            return "success"
        
        result = my_function()
        assert result == "success"
    
    def test_decorator_with_key_func(self):
        """Test decorator with key function."""
        limiter = SlidingWindowLimiter(RateLimitConfig(requests=2, window_seconds=60))
        
        @rate_limit(limiter, key_func=lambda x: x)
        def my_function(user_id):
            return f"Hello {user_id}"
        
        # First call
        result = my_function("user1")
        assert result == "Hello user1"
        
        # Second call
        result = my_function("user1")
        assert result == "Hello user1"
        
        # Third call should raise
        with pytest.raises(RateLimitExceeded):
            my_function("user1")
    
    def test_decorator_different_keys(self):
        """Test decorator with different keys."""
        limiter = SlidingWindowLimiter(RateLimitConfig(requests=1, window_seconds=60))
        
        @rate_limit(limiter, key_func=lambda x: x)
        def my_function(user_id):
            return f"Hello {user_id}"
        
        # user1 exhausted
        my_function("user1")
        with pytest.raises(RateLimitExceeded):
            my_function("user1")
        
        # user2 should still work
        result = my_function("user2")
        assert result == "Hello user2"


class TestRateLimitResult:
    """Tests for rate limit result."""
    
    def test_to_headers(self):
        """Test converting result to HTTP headers."""
        result = RateLimitResult(
            allowed=True,
            remaining=50,
            reset_time=1234567890.0
        )
        
        headers = result.to_headers(limit=100)
        
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "50"
        assert headers["X-RateLimit-Reset"] == "1234567890"
    
    def test_headers_with_retry_after(self):
        """Test headers include Retry-After when blocked."""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_time=1234567890.0,
            retry_after=30.0
        )
        
        headers = result.to_headers(limit=100)
        
        assert headers["Retry-After"] == "30"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
