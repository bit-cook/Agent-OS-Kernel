"""
验证工具模块 - 提供数据验证功能
"""

from typing import Any, Dict, List, Optional, Callable, Pattern
from dataclasses import dataclass
import re


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    
    @property
    def error_message(self) -> str:
        return "; ".join(self.errors) if self.errors else ""


class Validator:
    """数据验证器"""
    
    def __init__(self):
        self._rules: Dict[str, List[Callable]] = {}
        self._patterns: Dict[str, Pattern] = {}
    
    def add_rule(self, field: str, rule: Callable[[Any], bool], message: str):
        """添加验证规则"""
        if field not in self._rules:
            self._rules[field] = []
        self._rules[field].append((rule, message))
    
    def validate(self, data: Dict) -> ValidationResult:
        """验证数据"""
        errors = []
        
        for field, rules in self._rules.items():
            value = data.get(field)
            for rule, message in rules:
                if not rule(value):
                    errors.append(f"{field}: {message}")
        
        return ValidationResult(len(errors) == 0, errors)
    
    @staticmethod
    def email() -> Callable[[Any], bool]:
        """邮箱验证"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return lambda x: bool(re.match(pattern, x)) if x else False
    
    @staticmethod
    def url() -> Callable[[Any], bool]:
        """URL验证"""
        pattern = r'^https?://[^\s]+$'
        return lambda x: bool(re.match(pattern, x)) if x else False
    
    @staticmethod
    def min_length(min_len: int) -> Callable[[Any], bool]:
        """最小长度"""
        return lambda x: len(str(x)) >= min_len if x else False
    
    @staticmethod
    def max_length(max_len: int) -> Callable[[Any], bool]:
        """最大长度"""
        return lambda x: len(str(x)) <= max_len if x else False
    
    @staticmethod
    def min_value(min_val: int) -> Callable[[Any], bool]:
        """最小值"""
        return lambda x: x >= min_val if x is not None else False
    
    @staticmethod
    def max_value(max_val: int) -> Callable[[Any], bool]:
        """最大值"""
        return lambda x: x <= max_val if x is not None else False
    
    @staticmethod
    def required() -> Callable[[Any], bool]:
        """必填"""
        return lambda x: x is not None and x != ""
    
    @staticmethod
    def pattern(regex: str) -> Callable[[Any], bool]:
        """正则匹配"""
        compiled = re.compile(regex)
        return lambda x: bool(compiled.match(x)) if x else False


class SchemaValidator:
    """Schema验证器"""
    
    def __init__(self, schema: Dict):
        self.schema = schema
        self.validator = Validator()
        self._build_rules()
    
    def _build_rules(self):
        """根据schema构建规则"""
        for field, rules in self.schema.items():
            if isinstance(rules, list):
                for rule in rules:
                    if callable(rule):
                        self.validator.add_rule(field, rule, "Invalid")
    
    def validate(self, data: Dict) -> ValidationResult:
        """验证数据"""
        return self.validator.validate(data)


__all__ = ["Validator", "ValidationResult", "SchemaValidator"]
