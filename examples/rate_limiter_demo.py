"""
Rate Limiter Demo

Demonstrates various rate limiting algorithms and features:
- Sliding Window Algorithm
- Token Bucket Algorithm
- Multi-dimensional Rate Limiting
- Distributed Rate Limiting
- Decorator Usage
"""

import time
import threading
from agent_os_kernel.core.rate_limiter_enhanced import (
    SlidingWindowLimiter,
    TokenBucketLimiter,
    MultiDimensionalLimiter,
    DistributedRateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    rate_limit,
)


def demo_sliding_window():
    """Demonstrate sliding window rate limiting."""
    print("=" * 60)
    print("DEMO: Sliding Window Rate Limiter")
    print("=" * 60)
    
    # Configure: 5 requests per 10 seconds
    config = RateLimitConfig(requests=5, window_seconds=10)
    limiter = SlidingWindowLimiter(config)
    
    print(f"\nConfiguration: {config.requests} requests per {config.window_seconds} seconds")
    
    # Make requests up to the limit
    print("\nMaking requests:")
    for i in range(7):
        result = limiter.check(f"user_{i % 3}", 1)
        status = "✓ ALLOWED" if result.allowed else "✗ BLOCKED"
        print(f"  Request {i+1}: {status} (remaining: {result.remaining})")
        
        if not result.allowed:
            print(f"    Retry after: {result.retry_after:.2f} seconds")
    
    print("\n" + "-" * 60)
    print("Key Features:")
    print("- Simple counter-based approach")
    print("- Memory efficient for single endpoints")
    print("- Reset time based on oldest request in window")
    print()


def demo_token_bucket():
    """Demonstrate token bucket rate limiting."""
    print("=" * 60)
    print("DEMO: Token Bucket Rate Limiter")
    print("=" * 60)
    
    # Configure: 10 requests/second rate, burst up to 20
    config = RateLimitConfig(requests=10, window_seconds=1, burst=20)
    limiter = TokenBucketLimiter(config)
    
    print(f"\nConfiguration: {config.requests} tokens/second, burst={config.burst}")
    
    # Burst example
    print("\n1. Burst Example - Using all burst tokens:")
    result = limiter.check("burst_user", 20)
    status = "✓ ALLOWED" if result.allowed else "✗ BLOCKED"
    print(f"   20 requests at once: {status} (remaining: {result.remaining})")
    
    print("\n2. Immediate Refill Check:")
    result = limiter.check("burst_user", 1)
    status = "✓ ALLOWED" if result.allowed else "✗ BLOCKED"
    print(f"   Request after burst: {status}")
    
    print("\n3. Waiting for Refill (1 second):")
    print("   Waiting...")
    time.sleep(1.1)
    result = limiter.check("burst_user", 5)
    status = "✓ ALLOWED" if result.allowed else "✗ BLOCKED"
    print(f"   After refill (5 requests): {status} (remaining: {result.remaining})")
    
    print("\n" + "-" * 60)
    print("Key Features:")
    print("- Allows burst traffic up to bucket capacity")
    print("- Tokens refill at steady rate")
    print("- Smooth traffic shaping with burst allowance")
    print()


def demo_multi_dimensional():
    """Demonstrate multi-dimensional rate limiting."""
    print("=" * 60)
    print("DEMO: Multi-Dimensional Rate Limiter")
    print("=" * 60)
    
    limiter = MultiDimensionalLimiter()
    
    # Configure different limits for different dimensions
    limiter.add_dimension("user", "user1", RateLimitConfig(requests=100, window_seconds=3600))
    limiter.add_dimension("ip", "192.168.1.100", RateLimitConfig(requests=50, window_seconds=3600))
    limiter.add_dimension("endpoint", "/api/data", RateLimitConfig(requests=10, window_seconds=60))
    limiter.add_dimension("endpoint", "/api/upload", RateLimitConfig(requests=5, window_seconds=60))
    
    print("\nConfiguration:")
    print("  - User limit: 100 req/hour")
    print("  - IP limit: 50 req/hour")
    print("  - /api/data limit: 10 req/minute")
    print("  - /api/upload limit: 5 req/minute")
    
    # Simulate normal traffic
    print("\n1. Normal API Request to /api/data:")
    dimensions = {"user": "user1", "ip": "192.168.1.100", "endpoint": "/api/data"}
    result = limiter.check(dimensions, 1)
    print(f"   Status: {'✓ ALLOWED' if result.allowed else '✗ BLOCKED'}")
    print(f"   Remaining quota: {result.remaining}")
    
    # Exhaust endpoint limit
    print("\n2. Exhausting /api/data endpoint limit:")
    for i in range(10):
        result = limiter.check(dimensions, 1)
        if not result.allowed:
            print(f"   Request {i+1}: ✗ BLOCKED (most restrictive: endpoint)")
            print(f"   Retry after: {result.retry_after:.2f} seconds")
            break
    
    # Test different endpoint (should still work)
    print("\n3. Requesting different endpoint (/api/upload):")
    dimensions["endpoint"] = "/api/upload"
    result = limiter.check(dimensions, 1)
    print(f"   Status: {'✓ ALLOWED' if result.allowed else '✗ BLOCKED'}")
    
    print("\n" + "-" * 60)
    print("Key Features:")
    print("- Combine multiple rate limit dimensions")
    print("- Most restrictive limit is applied")
    print("- Different limits per endpoint/resource")
    print("- Useful for API gateways and microservices")
    print()


def demo_decorator():
    """Demonstrate decorator-based rate limiting."""
    print("=" * 60)
    print("DEMO: Rate Limit Decorator")
    print("=" * 60)
    
    # Create a limiter
    limiter = SlidingWindowLimiter(RateLimitConfig(requests=3, window_seconds=10))
    
    @rate_limit(limiter, key_func=lambda user_id: user_id)
    def get_user_data(user_id: str, resource: str = "profile"):
        """Simulated API endpoint."""
        return {"user": user_id, "data": f"Resource: {resource}"}
    
    @rate_limit(limiter, key_func=lambda req: req["user"])
    def process_request(request: dict):
        """Another endpoint example."""
        return {"status": "processed", "request": request}
    
    print("\n1. Using decorated function (user1):")
    for i in range(5):
        try:
            result = get_user_data("user1", f"item_{i}")
            print(f"   Call {i+1}: ✓ {result}")
        except RateLimitExceeded as e:
            print(f"   Call {i+1}: ✗ Rate limited! Retry after {e.retry_after:.2f}s")
    
    print("\n2. Different user (user2) still has quota:")
    try:
        result = get_user_data("user2")
        print(f"   Call 1: ✓ {result}")
    except RateLimitExceeded as e:
        print(f"   Call 1: ✗ Rate limited")
    
    print("\n3. Using with dictionary request:")
    try:
        result = process_request({"user": "user1", "action": "update"})
        print(f"   ✓ {result}")
    except RateLimitExceeded as e:
        print(f"   ✗ Rate limited")
    
    print("\n" + "-" * 60)
    print("Key Features:")
    print("- Easy integration with existing functions")
    print("- Key extraction from function arguments")
    print("- Automatic rate limit enforcement")
    print("- Exception-based error handling")
    print()


def demo_distributed_rate_limiting():
    """Demonstrate distributed rate limiting concepts."""
    print("=" * 60)
    print("DEMO: Distributed Rate Limiting")
    print("=" * 60)
    
    # Without Redis (local mode)
    limiter = DistributedRateLimiter(prefix="myapp")
    
    print("\n1. Local Mode (No Redis):")
    result = limiter.check("user1", 10, 60, "sliding")
    print(f"   Check result: allowed={result.allowed}, remaining={result.remaining}")
    
    result = limiter.check("user1", 10, 60, "token_bucket")
    print(f"   Token bucket: allowed={result.allowed}, remaining={result.remaining}")
    
    print("\n2. Key Design for Distributed Systems:")
    print("   - User ID: per-user limits")
    print("   - API Key: per-client limits")
    print("   - IP Address: per-origin limits")
    print("   - Composite: user+endpoint combinations")
    
    print("\n3. Redis Integration (Concept):")
    print("   # Would use Redis INCR or Lua scripts for atomic operations")
    print("   # Cache recent results for performance")
    print("   # Sync across multiple application instances")
    
    print("\n" + "-" * 60)
    print("Key Features:")
    print("- Consistent rate limiting across multiple servers")
    print("- Redis-backed for production deployments")
    print("- Local caching for performance")
    print("- Configurable prefix for multi-tenant isolation")
    print()


def demo_comparison():
    """Compare different algorithms."""
    print("=" * 60)
    print("DEMO: Algorithm Comparison")
    print("=" * 60)
    
    # Same limits for fair comparison
    config = RateLimitConfig(requests=5, window_seconds=5)
    
    sliding = SlidingWindowLimiter(config)
    token = TokenBucketLimiter(RateLimitConfig(
        requests=5, window_seconds=5, burst=5
    ))
    
    print("\nScenario: Sudden burst of 5 requests")
    
    print("\n  Sliding Window:")
    for i in range(5):
        result = sliding.check("user", 1)
        print(f"    Request {i+1}: allowed={result.allowed}, remaining={result.remaining}")
    result = sliding.check("user", 1)
    print(f"    Request 6: allowed={result.allowed} (exhausted)")
    
    print("\n  Token Bucket:")
    for i in range(5):
        result = token.check("user", 1)
        print(f"    Request {i+1}: allowed={result.allowed}, remaining={result.remaining:.1f}")
    result = token.check("user", 1)
    print(f"    Request 6: allowed={result.allowed}")
    
    print("\nScenario: Wait for refill (5.1 seconds)")
    time.sleep(5.1)
    
    print("\n  Sliding Window (old requests expired):")
    result = sliding.check("user", 1)
    print(f"    Request after wait: allowed={result.allowed}, remaining={result.remaining}")
    
    print("\n  Token Bucket (refilled tokens):")
    result = token.check("user", 1)
    print(f"    Request after wait: allowed={result.allowed}, remaining={result.remaining:.1f}")
    
    print("\n" + "-" * 60)
    print("Comparison Summary:")
    print("┌─────────────────┬────────────────────┬────────────────────┐")
    print("│ Feature         │ Sliding Window     │ Token Bucket       │")
    print("├─────────────────┼────────────────────┼────────────────────┤")
    print("│ Burst handling  │ Limited to window  │ Full burst support │")
    print("│ Smoothness     │ All-or-nothing     │ Gradual refill     │")
    print("│ Memory         │ O(window size)     │ O(num_buckets)     │")
    print("│ Use case       │ API endpoints      │ Rate shaping       │")
    print("└─────────────────┴────────────────────┴────────────────────┘")
    print()


def demo_threading():
    """Demonstrate thread-safe operation."""
    print("=" * 60)
    print("DEMO: Thread-Safe Rate Limiting")
    print("=" * 60)
    
    config = RateLimitConfig(requests=50, window_seconds=60)
    limiter = SlidingWindowLimiter(config)
    
    results = {"success": 0, "blocked": 0}
    lock = threading.Lock()
    
    def worker(worker_id: int):
        """Worker thread function."""
        for _ in range(15):
            result = limiter.check("shared_key", 1)
            with lock:
                if result.allowed:
                    results["success"] += 1
                else:
                    results["blocked"] += 1
    
    print(f"\nStarting 4 threads, each making 15 requests...")
    print(f"Total capacity: {config.requests} requests")
    print(f"Expected: {4*15} = 60 requests attempted, {config.requests} allowed")
    
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    print(f"\nResults:")
    print(f"  ✓ Allowed: {results['success']}")
    print(f"  ✗ Blocked: {results['blocked']}")
    print(f"  Total: {results['success'] + results['blocked']}")
    
    print("\n" + "-" * 60)
    print("Key Points:")
    print("- All limiters are thread-safe via internal locks")
    print("- Works correctly under concurrent access")
    print("- Race conditions are handled properly")
    print()


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("ADVANCED RATE LIMITER DEMONSTRATION")
    print("=" * 60)
    
    demos = [
        ("Sliding Window", demo_sliding_window),
        ("Token Bucket", demo_token_bucket),
        ("Multi-Dimensional", demo_multi_dimensional),
        ("Decorator Usage", demo_decorator),
        ("Distributed Rate Limiting", demo_distributed_rate_limiting),
        ("Algorithm Comparison", demo_comparison),
        ("Thread-Safe Operation", demo_threading),
    ]
    
    for name, demo_func in demos:
        try:
            demo_func()
            time.sleep(0.5)  # Brief pause between demos
        except KeyboardInterrupt:
            print("\nDemo interrupted by user.")
            break
    
    print("=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("\nFor more information, see:")
    print("- README.md")
    print("- API documentation")
    print("- Source code in agent_os_kernel/core/rate_limiter_enhanced.py")
    print()


if __name__ == "__main__":
    main()
