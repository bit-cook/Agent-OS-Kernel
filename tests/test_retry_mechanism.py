"""
重试机制测试模块
"""

import pytest
import time
from unittest.mock import Mock, patch

from agent_os_kernel.core.retry_mechanism import (
    RetryCondition,
    RetryExhaustedError,
    RetryMechanism,
    RetryPolicy,
    retry,
)


class TestRetryCondition:
    """测试重试条件判断器"""
    
    def test_should_retry_all_exceptions(self):
        """测试重试所有异常"""
        condition = RetryCondition(retry_on_exception=True)
        assert condition.should_retry(Exception("test")) is True
        assert condition.should_retry(ValueError("test")) is True
        assert condition.should_retry(TypeError("test")) is True
    
    def test_should_retry_specific_exception_types(self):
        """测试只重试特定异常类型"""
        condition = RetryCondition(
            retry_on_exception=True,
            exception_types=(ValueError, TypeError)
        )
        assert condition.should_retry(ValueError("test")) is True
        assert condition.should_retry(TypeError("test")) is True
        assert condition.should_retry(Exception("test")) is False
    
    def test_no_retry_on_exception(self):
        """测试不重试异常"""
        condition = RetryCondition(retry_on_exception=False)
        assert condition.should_retry(Exception("test")) is False
    
    def test_condition_callable(self):
        """测试条件可调用"""
        condition = RetryCondition(retry_on_exception=True)
        assert condition(Exception("test")) is True


class TestRetryPolicy:
    """测试重试策略"""
    
    def test_default_policy(self):
        """测试默认策略"""
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.base_delay == 1.0
        assert policy.exponential_base == 2.0
        assert policy.jitter is True
    
    def test_calculate_delay_exponential(self):
        """测试指数退避延迟计算"""
        policy = RetryPolicy(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )
        # 第一次重试：1.0 * 2^0 = 1.0
        assert policy.calculate_delay(0) == 1.0
        # 第二次重试：1.0 * 2^1 = 2.0
        assert policy.calculate_delay(1) == 2.0
        # 第三次重试：1.0 * 2^2 = 4.0
        assert policy.calculate_delay(2) == 4.0
        # 第四次重试：1.0 * 2^3 = 8.0
        assert policy.calculate_delay(3) == 8.0
    
    def test_max_delay_cap(self):
        """测试最大延迟限制"""
        policy = RetryPolicy(
            base_delay=10.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=False
        )
        # 第五次重试：10.0 * 2^4 = 160，但被限制为30
        assert policy.calculate_delay(4) == 30.0
    
    def test_exponential_backoff(self):
        """测试指数退避功能"""
        policy = RetryPolicy(
            base_delay=0.1,
            max_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )
        delays = [policy.calculate_delay(i) for i in range(5)]
        # 验证延迟呈指数增长
        for i in range(1, len(delays)):
            assert delays[i] >= delays[i-1]


class TestRetryMechanism:
    """测试重试机制"""
    
    def test_successful_first_attempt(self):
        """测试第一次尝试成功"""
        def success_func():
            return "success"
        
        mechanism = RetryMechanism()
        result = mechanism.execute(success_func)
        assert result == "success"
    
    def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        call_count = 0
        
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        mechanism = RetryMechanism(RetryPolicy(max_retries=2))
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            mechanism.execute(always_fail)
        
        assert exc_info.value.attempts == 3  # 3次调用（1次 + 2次重试）
        assert call_count == 3
    
    def test_retry_condition_filters_exceptions(self):
        """测试重试条件过滤异常"""
        call_count = 0
        
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise TypeError("Type error")
        
        # 只重试ValueError
        condition = RetryCondition(
            retry_on_exception=True,
            exception_types=(ValueError,)
        )
        mechanism = RetryMechanism(RetryPolicy(
            max_retries=2,
            retry_condition=condition
        ))
        
        with pytest.raises(TypeError):
            mechanism.execute(always_fail)
        
        assert call_count == 1  # 不应该重试
    
    def test_retry_timeout(self):
        """测试重试超时"""
        def slow_func():
            time.sleep(0.5)
            raise ValueError("Slow fail")
        
        mechanism = RetryMechanism(RetryPolicy(
            max_retries=5,
            base_delay=0.5,
            timeout=1.0
        ))
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            mechanism.execute(slow_func)
        
        assert "timeout" in str(exc_info.value).lower()
    
    def test_exponential_backoff(self):
        """测试指数退避"""
        call_times = []
        
        def timed_fail():
            call_times.append(time.time())
            raise ValueError("Fail")
        
        mechanism = RetryMechanism(RetryPolicy(
            max_retries=3,
            base_delay=0.1,
            exponential_base=2.0,
            jitter=False
        ))
        
        with pytest.raises(RetryExhaustedError):
            mechanism.execute(timed_fail)
        
        # 验证延迟递增
        for i in range(1, len(call_times)):
            interval = call_times[i] - call_times[i-1]
            assert interval >= 0.08  # 0.1 * 2^i - 小误差
    
    def test_retry_timeout_with_success(self):
        """测试在超时前成功"""
        call_count = 0
        
        def succeed_on_third():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"
        
        mechanism = RetryMechanism(RetryPolicy(
            max_retries=5,
            base_delay=0.01,
            timeout=5.0
        ))
        
        result = mechanism.execute(succeed_on_third)
        assert result == "success"
        assert call_count == 3


class TestRetryDecorator:
    """测试重试装饰器"""
    
    def test_decorator_success(self):
        """测试装饰器成功执行"""
        @retry(max_retries=3, base_delay=0.01)
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
    
    def test_decorator_retry(self):
        """测试装饰器重试"""
        call_count = 0
        
        @retry(max_retries=2, base_delay=0.01)
        def retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"
        
        result = retry_func()
        assert result == "success"
        assert call_count == 3
    
    def test_decorator_with_exception_types(self):
        """测试装饰器指定异常类型"""
        call_count = 0
        
        @retry(max_retries=2, base_delay=0.01, exception_types=(ValueError,))
        def specific_exception():
            nonlocal call_count
            call_count += 1
            raise ValueError("Value error")
        
        with pytest.raises(RetryExhaustedError):
            specific_exception()
        
        assert call_count == 3
    
    def test_decorator_timeout(self):
        """测试装饰器超时"""
        @retry(max_retries=5, base_delay=0.2, timeout=0.5)
        def slow_fail():
            time.sleep(0.3)
            raise ValueError("Fail")
        
        with pytest.raises(RetryExhaustedError):
            slow_fail()


class TestRetryExhaustedError:
    """测试RetryExhaustedError异常"""
    
    def test_error_properties(self):
        """测试异常属性"""
        original = ValueError("Original error")
        error = RetryExhaustedError(
            "Retry exhausted",
            original,
            attempts=3
        )
        
        assert error.last_exception is original
        assert error.attempts == 3
        assert "exhausted" in str(error).lower()


class TestRetryAsync:
    """测试异步重试"""
    
    @pytest.mark.asyncio
    async def test_async_retry_success(self):
        """测试异步重试成功"""
        call_count = 0
        
        async def async_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"
        
        mechanism = RetryMechanism(RetryPolicy(
            max_retries=5,
            base_delay=0.01
        ))
        
        result = await mechanism.execute_async(async_succeed)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_retry_exhausted(self):
        """测试异步重试耗尽"""
        call_count = 0
        
        async def async_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        mechanism = RetryMechanism(RetryPolicy(max_retries=2))
        
        with pytest.raises(RetryExhaustedError):
            await mechanism.execute_async(async_fail)
        
        assert call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
