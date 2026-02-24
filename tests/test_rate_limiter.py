# -*- coding: utf-8 -*-
"""
Tests for Rate Limiter Module
"""

import pytest
import time
import threading
from agent_os_kernel.core.rate_limiter import (
    TokenBucket,
    RateLimiter,
    RateLimitResult,
    create_rate_limiter,
)


class TestTokenBucket:
    """Tests for TokenBucket class."""
    
    def test_basic_consume(self):
        """Test basic token consumption."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        result = bucket.consume(1)
        assert result.allowed is True
        assert result.remaining == 9
    
    def test_consume_multiple(self):
        """Test consuming multiple tokens at once."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        result = bucket.consume(5)
        assert result.allowed is True
        assert result.remaining == 5
    
    def test_exhaust_bucket(self):
        """Test that requests are blocked when bucket is empty."""
        bucket = TokenBucket(capacity=3, refill_rate=1.0)
        
        # Consume all tokens
        bucket.consume(3)
        
        # Next request should be blocked
        result = bucket.consume(1)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
    
    def test_refill_tokens(self):
        """Test that tokens are refilled over time."""
        bucket = TokenBucket(capacity=5, refill_rate=2.0)  # 2 tokens per second
        
        # Consume all tokens
        bucket.consume(5)
        assert bucket.consume(1).allowed is False
        
        # Wait for refill
        time.sleep(1.1)
        
        # Should have at least 2 tokens now
        result = bucket.consume(2)
        assert result.allowed is True
    
    def test_reset(self):
        """Test resetting the bucket."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        bucket.consume(8)
        result = bucket.consume(1)
        assert result.allowed is False
        
        bucket.reset()
        
        result = bucket.consume(5)
        assert result.allowed is True
        assert result.remaining == 5
    
    def test_available_tokens(self):
        """Test checking available tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        assert bucket.available_tokens == 10
        
        bucket.consume(3)
        
        assert bucket.available_tokens == 7
    
    def test_max_capacity(self):
        """Test that tokens don't exceed capacity."""
        bucket = TokenBucket(capacity=5, refill_rate=10.0)
        
        bucket.consume(3)
        
        # Wait longer than needed for full refill
        time.sleep(1.0)
        
        # Should be at max capacity (5), not more
        assert bucket.available_tokens <= 5
    
    def test_thread_safety(self):
        """Test thread-safe operations."""
        bucket = TokenBucket(capacity=100, refill_rate=100.0)
        results = []
        
        def consume_tokens():
            for _ in range(30):
                result = bucket.consume(1)
                results.append(result.allowed)
        
        threads = [threading.Thread(target=consume_tokens) for _ in range(4)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All operations should be processed (thread-safe)
        assert len(results) == 120


class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    def test_basic_check(self):
        """Test basic rate limit check."""
        limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)
        
        result = limiter.check("user1", 1)
        assert result.allowed is True
        assert result.remaining == 9
    
    def test_different_keys_independent(self):
        """Test that different keys have separate limits."""
        limiter = RateLimiter(default_capacity=2, default_refill_rate=1.0)
        
        # Exhaust user1
        limiter.check("user1", 2)
        result = limiter.check("user1", 1)
        assert result.allowed is False
        
        # user2 should still have quota
        result = limiter.check("user2", 1)
        assert result.allowed is True
        assert result.remaining == 1
    
    def test_reset_key(self):
        """Test resetting a specific key."""
        limiter = RateLimiter(default_capacity=2, default_refill_rate=1.0)
        
        # Exhaust limit
        limiter.check("user1", 2)
        result = limiter.check("user1", 1)
        assert result.allowed is False
        
        # Reset
        limiter.reset("user1")
        
        # Should be able to make requests again
        result = limiter.check("user1", 2)
        assert result.allowed is True
    
    def test_reset_all(self):
        """Test resetting all keys."""
        limiter = RateLimiter(default_capacity=2, default_refill_rate=1.0)
        
        limiter.check("user1", 2)
        limiter.check("user2", 2)
        
        limiter.reset_all()
        
        assert limiter.check("user1", 2).allowed is True
        assert limiter.check("user2", 2).allowed is True
    
    def test_get_remaining(self):
        """Test getting remaining tokens."""
        limiter = RateLimiter(default_capacity=10, default_refill_rate=1.0)
        
        assert limiter.get_remaining("user1") == 10
        
        limiter.check("user1", 3)
        
        assert limiter.get_remaining("user1") == 7
    
    def test_set_custom_limit(self):
        """Test setting custom rate limit for a key."""
        limiter = RateLimiter(default_capacity=5, default_refill_rate=1.0)
        
        # Set custom limit
        limiter.set_limit("vip_user", 100, 10.0)
        
        result = limiter.check("vip_user", 50)
        assert result.allowed is True
        assert result.remaining == 50
        
        # Default key should still have default limit
        result = limiter.check("default", 5)
        assert result.remaining == 0
    
    def test_thread_safety(self):
        """Test thread-safe operations on limiter."""
        limiter = RateLimiter(default_capacity=200, default_refill_rate=100.0)
        results = []
        
        def make_requests():
            for _ in range(50):
                result = limiter.check("shared_key", 1)
                results.append(result.allowed)
        
        threads = [threading.Thread(target=make_requests) for _ in range(4)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have processed all 200 requests
        assert len(results) == 200


class TestRateLimitResult:
    """Tests for RateLimitResult class."""
    
    def test_allowed_result(self):
        """Test result when request is allowed."""
        result = RateLimitResult(
            allowed=True,
            remaining=50,
            reset_time=1234567890.0
        )
        
        assert result.allowed is True
        assert result.remaining == 50
        assert result.retry_after is None
    
    def test_blocked_result(self):
        """Test result when request is blocked."""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_time=1234567890.0,
            retry_after=30.0
        )
        
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 30.0


class TestCreateRateLimiter:
    """Tests for create_rate_limiter helper function."""
    
    def test_create_with_defaults(self):
        """Test creating rate limiter with default settings."""
        limiter = create_rate_limiter()
        
        result = limiter.check("test_key", 1)
        assert result.allowed is True
    
    def test_create_custom_settings(self):
        """Test creating rate limiter with custom settings."""
        limiter = create_rate_limiter(
            requests_per_second=5.0,
            burst_capacity=20
        )
        
        # Should allow burst of 20
        result = limiter.check("test_key", 20)
        assert result.allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
