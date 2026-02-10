"""测试工具系统"""
from abc import abstractmethod

import pytest
from agent_os_kernel.tools.base import Tool, SimpleTool, ToolParameter
from agent_os_kernel.tools.registry import ToolRegistry
from agent_os_kernel.tools.builtin import (
    CalculatorTool,
    FileReadTool,
    JsonTool,
)


class TestCalculatorTool:
    def test_basic_calculation(self):
        tool = CalculatorTool()
        result = tool.execute(expression="2 + 2")
        
        assert result['success'] is True
        assert result['data'] == 4
    
    def test_math_functions(self):
        tool = CalculatorTool()
        result = tool.execute(expression="sqrt(16)")
        
        assert result['success'] is True
        assert result['data'] == 4.0
    
    def test_invalid_expression(self):
        tool = CalculatorTool()
        result = tool.execute(expression="__import__('os').system('ls')")
        
        assert result['success'] is False
        assert 'Disallowed name' in result['error']


class TestJsonTool:
    def test_parse(self):
        tool = JsonTool()
        result = tool.execute(action="parse", data='{"key": "value"}')
        
        assert result['success'] is True
        assert result['data'] == {'key': 'value'}
    
    def test_format(self):
        tool = JsonTool()
        result = tool.execute(action="format", data='{"key":"value"}')
        
        assert result['success'] is True
        assert '"key": "value"' in result['data']
    
    def test_extract(self):
        tool = JsonTool()
        data = '{"outer": {"inner": "value"}}'
        result = tool.execute(action="extract", data=data, path="outer.inner")
        
        assert result['success'] is True
        assert result['data'] == "value"


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = CalculatorTool()
        
        registry.register(tool)
        retrieved = registry.get("calculator")
        
        assert retrieved is not None
        assert retrieved.name() == "calculator"
    
    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        registry.register(FileReadTool())
        
        tools = registry.list_tools()
        
        assert len(tools) == 2
        assert any(t['name'] == 'calculator' for t in tools)
    
    def test_execute(self):
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        
        result = registry.execute("calculator", expression="5 * 5")
        
        assert result['success'] is True
        assert result['data'] == 25
    
    def test_execute_unknown_tool(self):
        registry = ToolRegistry()
        
        result = registry.execute("unknown_tool")
        
        assert result['success'] is False
        assert "not found" in result['error']


class TestSimpleTool:
    def test_simple_function_wrapper(self):
        def greet(name):
            return f"Hello, {name}!"
        
        tool = SimpleTool("greet", "Greet someone", greet)
        result = tool.execute(name="World")
        
        assert result['success'] is True
        assert result['data'] == "Hello, World!"
    
    def test_error_handling(self):
        def fail():
            raise ValueError("Test error")
        
        tool = SimpleTool("fail", "Fail", fail)
        result = tool.execute()
        
        assert result['success'] is False
        assert "Test error" in result['error']
