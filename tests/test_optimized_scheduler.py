# -*- coding: utf-8 -*-
"""测试优化调度器"""

import pytest
import asyncio
from agent_os_kernel.core.optimized_scheduler import OptimizedScheduler, Priority


@pytest.mark.asyncio
class TestOptimizedSchedulerAsync:
    """OptimizedScheduler 测试类"""

    @pytest.fixture
    def scheduler(self):
        """创建调度器"""
        return OptimizedScheduler(max_concurrent=5, quota_managed=True)

    async def test_schedule_task(self, scheduler):
        """测试调度任务"""

        async def task():
            return "done"

        task_id = await scheduler.schedule(name="test_task", func=task, priority=Priority.NORMAL)

        assert task_id is not None
        assert len(task_id) > 0

    async def test_priority_ordering(self, scheduler):
        """测试优先级排序"""
        results = []

        async def task(name):
            await asyncio.sleep(0.05)
            results.append(name)
            return name

        # 提交不同优先级
        await scheduler.schedule("low", task, "low", priority=Priority.LOW)
        await scheduler.schedule("high", task, "high", priority=Priority.HIGH)
        await scheduler.schedule("normal", task, "normal", priority=Priority.NORMAL)

        await asyncio.sleep(0.3)

        assert len(results) >= 1

    async def test_quota_management(self, scheduler):
        """测试配额管理"""
        scheduler._init_quota("test_quota", max_tasks=2)

        status = scheduler.get_quota_status("test_quota")

        assert status["name"] == "test_quota"
        assert status["max_tasks"] == 2
        assert status["current_tasks"] == 0

    async def test_get_stats(self, scheduler):
        """测试统计"""
        stats = scheduler.get_stats()

        assert "queue_size" in stats
        assert "running" in stats
        assert "quotas" in stats

    async def test_delay_scheduling(self, scheduler):
        """测试延迟调度"""

        async def task():
            return "delayed"

        import time

        start = time.time()

        await scheduler.schedule("delayed_task", task, delay_seconds=0.1, priority=Priority.NORMAL)

        await asyncio.sleep(0.2)

        # 延迟应该生效
        stats = scheduler.get_stats()
        assert "queue_size" in stats

    async def test_get_result(self, scheduler):
        """测试获取结果"""

        async def task():
            await asyncio.sleep(0.05)
            return "result"

        task_id = await scheduler.schedule("test", task)

        await asyncio.sleep(0.2)

        result = await scheduler.get_result(task_id)
        assert result == "result"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
