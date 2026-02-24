"""
数据验证器模块 - Data Validator

提供通用的数据验证功能，包括类型检查、范围验证、格式验证等。

功能:
- 类型检查 (Type Checking)
- 范围验证 (Range Validation) 
- 格式验证 (Format Validation)
- 自定义验证规则 (Custom Validation Rules)
"""

import re
from typing import Any, Callable, Optional, Union


class ValidationError(Exception):
    """验证错误异常"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class Validator:
    """验证器主类"""
    
    @staticmethod
    def type_check(
        expected_type: Union[type, tuple[type, ...]],
        field: Optional[str] = None
    ) -> Callable[[Any], None]:
        """
        类型检查验证器
        
        Args:
            expected_type: 期望的类型或类型元组
            field: 字段名称
            
        Returns:
            验证函数
        """
        def validate(value: Any) -> None:
            if not isinstance(value, expected_type):
                raise ValidationError(
                    f"Expected type {expected_type}, got {type(value)}",
                    field=field,
                    value=value
                )
        return validate
    
    @staticmethod
    def range_check(
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        field: Optional[str] = None
    ) -> Callable[[Union[int, float]], None]:
        """
        范围验证器
        
        Args:
            min_value: 最小值
            max_value: 最大值
            field: 字段名称
            
        Returns:
            验证函数
        """
        def validate(value: Union[int, float]) -> None:
            if min_value is not None and value < min_value:
                raise ValidationError(
                    f"Value {value} is less than minimum {min_value}",
                    field=field,
                    value=value
                )
            if max_value is not None and value > max_value:
                raise ValidationError(
                    f"Value {value} is greater than maximum {max_value}",
                    field=field,
                    value=value
                )
        return validate
    
    @staticmethod
    def length_check(
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        field: Optional[str] = None
    ) -> Callable[[str], None]:
        """
        长度验证器
        
        Args:
            min_length: 最小长度
            max_length: 最大长度
            field: 字段名称
            
        Returns:
            验证函数
        """
        def validate(value: str) -> None:
            if min_length is not None and len(value) < min_length:
                raise ValidationError(
                    f"Length {len(value)} is less than minimum {min_length}",
                    field=field,
                    value=value
                )
            if max_length is not None and len(value) > max_length:
                raise ValidationError(
                    f"Length {len(value)} is greater than maximum {max_length}",
                    field=field,
                    value=value
                )
        return validate
    
    @staticmethod
    def regex_check(
        pattern: str,
        field: Optional[str] = None
    ) -> Callable[[str], None]:
        """
        正则表达式验证器
        
        Args:
            pattern: 正则表达式模式
            field: 字段名称
            
        Returns:
            验证函数
        """
        regex = re.compile(pattern)
        
        def validate(value: str) -> None:
            if not regex.match(value):
                raise ValidationError(
                    f"Value does not match pattern {pattern}",
                    field=field,
                    value=value
                )
        return validate
    
    @staticmethod
    def choice_check(
        valid_choices: set,
        field: Optional[str] = None
    ) -> Callable[[Any], None]:
        """
        选项验证器
        
        Args:
            valid_choices: 有效选项集合
            field: 字段名称
            
        Returns:
            验证函数
        """
        def validate(value: Any) -> None:
            if value not in valid_choices:
                raise ValidationError(
                    f"Value {value} is not in valid choices {valid_choices}",
                    field=field,
                    value=value
                )
        return validate
    
    @staticmethod
    def custom_check(
        validate_func: Callable[[Any], bool],
        error_message: str,
        field: Optional[str] = None
    ) -> Callable[[Any], None]:
        """
        自定义验证器
        
        Args:
            validate_func: 验证函数，返回True表示通过
            error_message: 错误消息
            field: 字段名称
            
        Returns:
            验证函数
        """
        def validate(value: Any) -> None:
            if not validate_func(value):
                raise ValidationError(error_message, field=field, value=value)
        return validate


class DataValidator:
    """数据验证主类"""
    
    def __init__(self):
        self.validators = []
    
    def add_validator(
        self,
        validate_func: Callable[[Any], None],
        field: Optional[str] = None
    ) -> 'DataValidator':
        """
        添加验证规则
        
        Args:
            validate_func: 验证函数
            field: 字段名称
            
        Returns:
            self
        """
        self.validators.append((field, validate_func))
        return self
    
    def validate(self, data: dict) -> dict:
        """
        验证数据
        
        Args:
            data: 要验证的数据字典
            
        Returns:
            验证通过的数据
            
        Raises:
            ValidationError: 验证失败
        """
        validated_data = {}
        
        for field, validate_func in self.validators:
            if field is not None and field in data:
                validate_func(data[field])
                validated_data[field] = data[field]
            elif field is None:
                # 全局验证
                validate_func(data)
        
        return validated_data


def validate(
    schema: dict[str, Callable[[Any], None]]
) -> Callable[[dict], dict]:
    """
    数据验证装饰器
    
    Args:
        schema: 验证模式，字段名到验证函数的映射
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[[dict], dict]) -> Callable[[dict], dict]:
        def wrapper(data: dict) -> dict:
            validator = DataValidator()
            for field, validate_func in schema.items():
                validator.add_validator(validate_func, field)
            return validator.validate(data)
        
        def wrapper_async(data: dict) -> dict:
            return wrapper(data)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return wrapper_async
        return wrapper
    return decorator
