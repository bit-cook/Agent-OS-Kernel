"""
重试机制模块 - Retry Mechanism

提供指数退避、最大重试次数、重试条件和重试超时等功能。

功能:
- 指数退避 (Exponential Backoff)
- 最大重试次数 (Max Retries)
- 重试条件 (Retry Conditions)
- 重试超时 (Retry Timeout)
"""

import asyncio
import functools
import time
from typing import Any, Callable, Optional, Type, Union


class RetryExhaustedError(Exception):
    """重试次数耗尽异常"""
    
    def __init__(self, message: str, last_exception: Exception, attempts: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


class RetryCondition:
    """重试条件判断器"""
    
    def __init__(self, retry_on_exception: bool = True, 
                 exception_types: Optional[tuple[Type[Exception], ...]] = None):
        """
        初始化重试条件
        
        Args:
            retry_on_exception: 是否在发生异常时重试
            exception_types: 指定重试的异常类型，为None时重试所有异常
        """
        self.retry_on_exception = retry_on_exception
        self.exception_types = exception_types
    
    def should_retry(self, exception: Exception) -> bool:
        """
        判断是否应该重试
        
        Args:
            exception: 捕获的异常
            
        Returns:
            是否应该重试
        """
        if not self.retry_on_exception:
            return False
        
        if self.exception_types is None:
            return True
        
        return isinstance(exception, self.exception_types)
    
    def __call__(self, exception: Exception) -> bool:
        """使对象可调用"""
        return self.should_retry(exception)


class RetryPolicy:
    """重试策略配置"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_condition: Optional[RetryCondition] = None,
        timeout: Optional[float] = None
    ):
        """
        初始化重试策略
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            exponential_base: 指数基数
            jitter: 是否添加随机抖动
            retry_condition: 重试条件判断器
            timeout: 总超时时间（秒）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_condition = retry_condition or RetryCondition()
        self.timeout = timeout
    
    def calculate_delay(self, attempt: int) -> float:
        """
        计算延迟时间
        
        Args:
            attempt: 当前重试次数（从0开始）
            
        Returns:
            延迟时间（秒）
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # 添加±25%的随机抖动
            import random
            jitter_range = delay * 0.25
            delay = delay + random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)
        
        return delay


class RetryMechanism:
    """重试机制主类"""
    
    def __init__(self, policy: Optional[RetryPolicy] = None):
        """
        初始化重试机制
        
        Args:
            policy: 重试策略
        """
        self.policy = policy or RetryPolicy()
    
    def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        同步执行带重试的函数
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            RetryExhaustedError: 重试次数耗尽
        """
        start_time = time.time()
        last_exception = None
        
        for attempt in range(self.policy.max_retries + 1):
            # 检查超时
            if self.policy.timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= self.policy.timeout:
                    raise RetryExhaustedError(
                        f"Retry timeout exceeded after {attempt} attempts",
                        last_exception or Exception("Timeout"),
                        attempt
                    )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # 检查是否应该重试
                if not self.policy.retry_condition.should_retry(e):
                    raise
                
                # 检查是否还有重试机会
                if attempt >= self.policy.max_retries:
                    raise RetryExhaustedError(
                        f"Retry exhausted after {self.policy.max_retries + 1} attempts",
                        e,
                        self.policy.max_retries + 1
                    )
                
                # 计算并等待延迟
                delay = self.policy.calculate_delay(attempt)
                if self.policy.timeout is not None:
                    remaining = self.policy.timeout - (time.time() - start_time)
                    if remaining <= 0:
                        raise RetryExhaustedError(
                            "Retry timeout exceeded",
                            e,
                            attempt + 1
                        )
                    delay = min(delay, remaining)
                
                time.sleep(delay)
        
        # 理论上不会到达这里
        raise last_exception
    
    async def execute_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        异步执行带重试的函数
        
        Args:
            func: 异步函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            RetryExhaustedError: 重试次数耗尽
        """
        start_time = time.time()
        last_exception = None
        
        for attempt in range(self.policy.max_retries + 1):
            # 检查超时
            if self.policy.timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= self.policy.timeout:
                    raise RetryExhaustedError(
                        f"Retry timeout exceeded after {attempt} attempts",
                        last_exception or Exception("Timeout"),
                        attempt
                    )
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # 检查是否应该重试
                if not self.policy.retry_condition.should_retry(e):
                    raise
                
                # 检查是否还有重试机会
                if attempt >= self.policy.max_retries:
                    raise RetryExhaustedError(
                        f"Retry exhausted after {self.policy.max_retries + 1} attempts",
                        e,
                        self.policy.max_retries + 1
                    )
                
                # 计算并等待延迟
                delay = self.policy.calculate_delay(attempt)
                if self.policy.timeout is not None:
                    remaining = self.policy.timeout - (time.time() - start_time)
                    if remaining <= 0:
                        raise RetryExhaustedError(
                            "Retry timeout exceeded",
                            e,
                            attempt + 1
                        )
                    delay = min(delay, remaining)
                
                await asyncio.sleep(delay)
        
        # 理论上不会到达这里
        raise last_exception
    
    def decorate(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        装饰器方式使用重试机制
        
        Args:
            func: 要装饰的函数
            
        Returns:
            装饰后的函数
        """
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.execute(func, *args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await self.execute_async(func, *args, **kwargs)
        
        # 根据原函数类型返回对应的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on_exception: bool = True,
    exception_types: Optional[tuple[Type[Exception], ...]] = None,
    timeout: Optional[float] = None
) -> Callable[..., Any]:
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数基数
        jitter: 是否添加随机抖动
        retry_on_exception: 是否在发生异常时重试
        exception_types: 指定重试的异常类型
        timeout: 总超时时间（秒）
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        retry_condition = RetryCondition(
            retry_on_exception=retry_on_exception,
            exception_types=exception_types
        )
        policy = RetryPolicy(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retry_condition=retry_condition,
            timeout=timeout
        )
        mechanism = RetryMechanism(policy)
        return mechanism.decorate(func)
    return decorator
