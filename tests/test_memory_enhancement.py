# -*- coding: utf-8 -*-
"""测试记忆增强系统"""

import pytest
import asyncio
from agent_os_kernel.core.memory_feedback import (
    MemoryFeedbackSystem, FeedbackType
)
from agent_os_kernel.core.tool_memory import ToolMemory, ToolStatus


class TestMemoryFeedback:
    """MemoryFeedbackSystem 测试类"""
    
    @pytest.fixture
    def feedback(self):
        """创建反馈系统"""
        return MemoryFeedbackSystem()
    
    async def test_create_feedback(self, feedback):
        """测试创建反馈"""
        feedback_id = await feedback.create_feedback(
            memory_id="mem-001",
            feedback_type=FeedbackType.CORRECT,
            feedback_content="正确内容",
            reason="原内容错误",
            original_content="错误内容"
        )
        
        assert feedback_id is not None
        assert len(feedback_id) > 0
    
    async def test_apply_feedback(self, feedback):
        """测试应用反馈"""
        feedback_id = await feedback.create_feedback(
            memory_id="mem-001",
            feedback_type=FeedbackType.CORRECT,
            feedback_content="正确内容",
            reason="测试"
        )
        
        result = await feedback.apply_feedback(feedback_id)
        assert result is True
        
        # 再次应用应该失败
        result = await feedback.apply_feedback(feedback_id)
        assert result is False
    
    async def test_get_pending_feedbacks(self, feedback):
        """测试获取待处理反馈"""
        await feedback.create_feedback("mem-001", FeedbackType.CORRECT, "内容1", "原因1")
        await feedback.create_feedback("mem-002", FeedbackType.SUPPLEMENT, "内容2", "原因2")
        
        pending = await feedback.get_pending_feedbacks()
        assert len(pending) == 2
    
    async def test_get_feedback_history(self, feedback):
        """测试获取反馈历史"""
        await feedback.create_feedback("mem-001", FeedbackType.CORRECT, "内容1", "原因1")
        await feedback.create_feedback("mem-001", FeedbackType.SUPPLEMENT, "内容2", "原因2")
        
        history = await feedback.get_feedback_history("mem-001")
        assert len(history) == 2
    
    async def test_delete_feedback(self, feedback):
        """测试删除反馈"""
        feedback_id = await feedback.create_feedback(
            "mem-001", FeedbackType.CORRECT, "内容", "原因"
        )
        
        result = await feedback.delete_feedback(feedback_id)
        assert result is True
        
        # 再次删除应该失败
        result = await feedback.delete_feedback(feedback_id)
        assert result is False
    
    def test_get_stats(self, feedback):
        """测试统计"""
        stats = feedback.get_stats()
        
        assert "total_feedbacks" in stats
        assert "pending" in stats
        assert "applied" in stats


class TestToolMemory:
    """ToolMemory 测试类"""
    
    @pytest.fixture
    def tool_memory(self):
        """创建工具记忆"""
        return ToolMemory(max_history=100)
    
    async def test_record_call(self, tool_memory):
        """测试记录调用"""
        call_id = await tool_memory.record_call(
            tool_name="search",
            arguments={"query": "test"},
            result={"success": True},
            status=ToolStatus.SUCCESS,
            duration_ms=100.5
        )
        
        assert call_id is not None
        assert len(call_id) > 0
    
    async def test_get_tool_history(self, tool_memory):
        """测试获取历史"""
        await tool_memory.record_call("search", {"q": "1"}, {}, ToolStatus.SUCCESS, 100)
        await tool_memory.record_call("search", {"q": "2"}, {}, ToolStatus.SUCCESS, 100)
        await tool_memory.record_call("read", {"f": "1"}, {}, ToolStatus.SUCCESS, 50)
        
        history = await tool_memory.get_tool_history(tool_name="search")
        assert len(history) == 2
        
        all_history = await tool_memory.get_tool_history()
        assert len(all_history) == 3
    
    async def test_get_tool_statistics(self, tool_memory):
        """测试获取统计"""
        await tool_memory.record_call("search", {}, {}, ToolStatus.SUCCESS, 100)
        await tool_memory.record_call("search", {}, {}, ToolStatus.SUCCESS, 100)
        await tool_memory.record_call("read", {}, {}, ToolStatus.FAILED, 50)
        
        stats = await tool_memory.get_tool_statistics()
        
        assert stats["total_calls"] == 3
        assert stats["success_rate"] > 0
    
    async def test_get_frequently_used_tools(self, tool_memory):
        """测试获取常用工具"""
        for i in range(5):
            await tool_memory.record_call("search", {}, {}, ToolStatus.SUCCESS, 100)
        for i in range(3):
            await tool_memory.record_call("read", {}, {}, ToolStatus.SUCCESS, 50)
        
        top = await tool_memory.get_frequently_used_tools(2)
        
        assert len(top) == 2
        assert top[0]["tool_name"] == "search"
    
    async def test_get_failed_tools(self, tool_memory):
        """测试获取失败工具"""
        await tool_memory.record_call("tool1", {}, {}, ToolStatus.SUCCESS, 100)
        await tool_memory.record_call("tool2", {}, {}, ToolStatus.FAILED, 50)
        await tool_memory.record_call("tool2", {}, {}, ToolStatus.FAILED, 50)
        
        failed = await tool_memory.get_failed_tools()
        
        assert len(failed) >= 1
    
    async def test_get_slow_tools(self, tool_memory):
        """测试获取慢速工具"""
        await tool_memory.record_call("fast_tool", {}, {}, ToolStatus.SUCCESS, 10)
        await tool_memory.record_call("slow_tool", {}, {}, ToolStatus.SUCCESS, 2000)
        
        slow = await tool_memory.get_slow_tools(threshold_ms=100)
        
        assert len(slow) >= 1
    
    async def test_suggest_tools_for_task(self, tool_memory):
        """测试任务推荐"""
        # 先记录一些调用
        await tool_memory.record_call("search", {}, {}, ToolStatus.SUCCESS, 100)
        await tool_memory.record_call("read_file", {}, {}, ToolStatus.SUCCESS, 50)
        
        suggestions = await tool_memory.suggest_tools_for_task("search for information")
        
        assert "search" in suggestions
    
    def test_clear_history(self, tool_memory):
        """测试清空历史"""
        tool_memory._calls = [1, 2, 3]
        tool_memory._tool_stats = {"a": {}}
        
        tool_memory.clear_history()
        
        assert len(tool_memory._calls) == 0
        assert len(tool_memory._tool_stats) == 0
    
    def test_get_stats(self, tool_memory):
        """测试统计"""
        stats = tool_memory.get_stats()
        
        assert "total_calls" in stats
        assert "tools_count" in stats
        assert "max_history" in stats
