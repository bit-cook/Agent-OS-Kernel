"""测试熔断器"""

import pytest
from agent_os_kernel.core.circuit_breaker import (
    CircuitBreaker, CircuitState, CircuitConfig
)


class TestCircuitBreaker:
    """测试熔断器"""
    
    def test_initialization(self):
        """测试初始化"""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.name == "test"
    
    def test_closed_state(self):
        """测试关闭状态"""
        cb = CircuitBreaker("test", CircuitConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=60
        ))
        
        assert cb.state == CircuitState.CLOSED
    
    def test_metrics(self):
        """测试指标"""
        cb = CircuitBreaker("test")
        metrics = cb.metrics
        
        assert hasattr(metrics, 'total_requests')
        assert hasattr(metrics, 'failed_requests')
        assert metrics.total_requests == 0
    
    def test_reset(self):
        """测试重置"""
        cb = CircuitBreaker("test")
        cb.reset()
        
        assert cb.state == CircuitState.CLOSED


class TestCircuitState:
    """测试熔断状态"""
    
    def test_state_values(self):
        """测试状态值"""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitConfig:
    """测试熔断配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = CircuitConfig()
        
        assert config.failure_threshold == 5
        assert config.timeout_seconds == 30.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = CircuitConfig(
            failure_threshold=10,
            success_threshold=5,
            timeout_seconds=120.0
        )
        
        assert config.failure_threshold == 10
        assert config.success_threshold == 5
        assert config.timeout_seconds == 120.0
