"""测试性能指标收集器"""

import pytest
import time
from agent_os_kernel.core.metrics import MetricsCollector, RateLimiter, CircuitBreaker


class TestMetricsCollector:
    """测试 MetricsCollector"""
    
    def test_initialization(self):
        collector = MetricsCollector()
        
        assert collector.window_size == 60
        assert collector.max_history == 3600
        assert len(collector._cpu_history) == 0
    
    def test_record_cpu(self):
        collector = MetricsCollector()
        
        collector.record_cpu(50.0)
        collector.record_cpu(75.0)
        
        assert len(collector._cpu_history) == 2
        assert collector._cpu_history[0] == 50.0
    
    def test_record_memory(self):
        collector = MetricsCollector()
        
        collector.record_memory(60.0)
        
        assert len(collector._memory_history) == 1
        assert collector._memory_history[0] == 60.0
    
    def test_record_context_hit_rate(self):
        collector = MetricsCollector()
        
        collector.record_context_hit_rate(0.95)
        
        assert len(collector._context_hit_history) == 1
        assert collector._context_hit_history[0] == 0.95
    
    def test_record_swap(self):
        collector = MetricsCollector()
        
        collector.record_swap()
        collector.record_swap()
        
        assert collector.get_total_swaps() == 2
    
    def test_get_average_cpu(self):
        collector = MetricsCollector()
        
        collector.record_cpu(10.0)
        collector.record_cpu(20.0)
        collector.record_cpu(30.0)
        
        avg = collector.get_average_cpu()
        assert avg == 20.0
    
    def test_get_average_cpu_with_time_window(self):
        collector = MetricsCollector()
        
        collector.record_cpu(10.0)
        time.sleep(0.1)  # Small delay
        collector.record_cpu(90.0)
        
        # Only recent values should count
        avg = collector.get_average_cpu(seconds=1)
        # Should be around 50 (10 + 90) / 2
        assert 40 <= avg <= 60
    
    def test_get_average_memory(self):
        collector = MetricsCollector()
        
        collector.record_memory(40.0)
        collector.record_memory(60.0)
        
        avg = collector.get_average_memory()
        assert avg == 50.0
    
    def test_get_context_hit_rate(self):
        collector = MetricsCollector()
        
        collector.record_context_hit_rate(0.8)
        collector.record_context_hit_rate(0.9)
        
        rate = collector.get_context_hit_rate()
        assert rate == 0.85
    
    def test_get_metrics(self):
        collector = MetricsCollector()
        
        collector.record_cpu(50.0)
        collector.record_memory(60.0)
        collector.record_context_hit_rate(0.95)
        collector.record_swap()
        
        metrics = collector.get_metrics(active_agents=5, queued_agents=2)
        
        assert metrics.active_agents == 5
        assert metrics.queued_agents == 2
        assert metrics.cpu_usage > 0
        assert metrics.memory_usage > 0
    
    def test_get_history(self):
        collector = MetricsCollector()
        
        collector.record_cpu(10.0)
        collector.record_cpu(20.0)
        collector.record_cpu(30.0)
        
        history = collector.get_history(seconds=60)
        
        assert 'timestamps' in history
        assert 'cpu' in history
        assert len(history['cpu']) == 3
    
    def test_cleanup_old_data(self):
        collector = MetricsCollector(window_size=1)
        
        collector.record_cpu(10.0)
        time.sleep(1.5)  # Wait for data to expire
        
        collector.record_cpu(20.0)
        
        # Old data should be cleaned up
        avg = collector.get_average_cpu(seconds=1)
        assert 15 <= avg <= 25


class TestRateLimiter:
    """测试 RateLimiter"""
    
    def test_initialization(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 60
    
    def test_allow_requests(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        assert limiter.allow() is True
        assert limiter.allow() is True
        assert limiter.allow() is True
        assert limiter.allow() is False  # Too many
    
    def test_remaining_requests(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        limiter.allow()
        limiter.allow()
        
        assert limiter.remaining() == 3
    
    def test_reset(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        limiter.allow()
        limiter.allow()
        assert limiter.remaining() == 0
        
        limiter.reset()
        assert limiter.remaining() == 2


class TestCircuitBreaker:
    """测试 CircuitBreaker"""
    
    def test_initialization(self):
        breaker = CircuitBreaker(failure_threshold=5, recovery_time=60)
        
        assert breaker.failure_threshold == 5
        assert breaker.recovery_time == 60
        assert breaker.get_state() == "CLOSED"
    
    def test_allow_requests_when_closed(self):
        breaker = CircuitBreaker()
        
        assert breaker.allow() is True
    
    def test_record_success(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_time=60)
        
        breaker.record_success()
        breaker.record_success()
        
        assert breaker._failure_count == 0
    
    def test_record_failure(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_time=60)
        
        breaker.record_failure()
        breaker.record_failure()
        
        assert breaker._failure_count == 2
        assert breaker.get_state() == "CLOSED"
    
    def test_opens_after_threshold(self):
        breaker = CircuitBreaker(failure_threshold=2, recovery_time=60)
        
        breaker.record_failure()
        breaker.record_failure()
        
        assert breaker.get_state() == "OPEN"
        assert breaker.allow() is False
    
    def test_recovery_after_time(self):
        breaker = CircuitBreaker(failure_threshold=1, recovery_time=1)
        
        breaker.record_failure()
        assert breaker.get_state() == "OPEN"
        assert breaker.allow() is False
        
        time.sleep(1.1)  # Wait for recovery
        
        assert breaker.get_state() == "HALF_OPEN"
        assert breaker.allow() is True
