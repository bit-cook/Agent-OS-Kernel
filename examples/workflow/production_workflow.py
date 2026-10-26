# -*- coding: utf-8 -*-
"""
完整生产环境工作流示例

演示如何使用 Agent OS Kernel 构建完整的生产环境应用。
"""

import asyncio
import logging
from datetime import datetime
from agent_os_kernel import (
    AgentOSKernel,
    SecurityPolicy,
    PermissionLevel
)
from agent_os_kernel.core.agent_definition import AgentDefinition
from agent_os_kernel.core.scheduler import ResourceQuota
from agent_os_kernel.core.agent_pool import AgentPool
from agent_os_kernel.core.rate_limiter import RateLimitConfig, RateLimiter
from agent_os_kernel.core.enhanced_memory import EnhancedMemory

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionWorkflow:
    """生产环境工作流"""
    
    def __init__(self):
        self.kernel = None
        self.agent_pool = None
        self.rate_limiter = None
        self.memory = None
        self.initialized = False
    
    async def initialize(self):
        """初始化系统"""
        logger.info("Initializing production workflow...")
        
        # 1. 创建内核
        self.kernel = AgentOSKernel()
        
        # 2. 配置资源配额
        quota = ResourceQuota(
            max_tokens_per_window=128000,
            max_api_calls_per_window=1000
        )
        # 应用到调度器的配额管理器
        self.kernel.scheduler.quota_manager.quota = quota
        
        # 3. 配置安全策略
        policy = SecurityPolicy(
            permission_level=PermissionLevel.STANDARD,
            allowed_paths=["/workspace"],
            blocked_paths=["/etc", "/root"]
        )
        # 应用到内核: 为 Agent 绑定安全策略
        self.policy = policy
        self.kernel.spawn_agent(
            name="SecureWorker",
            task="在安全策略下执行任务",
            priority=50,
            policy=policy,
        )
        
        # 4. 初始化 Agent 池
        self.agent_pool = AgentPool(
            max_size=10,
            idle_timeout=3600,
            cleanup_interval=300
        )
        await self.agent_pool.initialize()
        
        # 5. 初始化速率限制器
        self.rate_limiter = RateLimiter(
            RateLimitConfig(
                requests_per_second=10.0,
                requests_per_minute=600.0,
                burst_size=20
            ),
            name="production"
        )
        
        # 6. 初始化内存系统
        self.memory = EnhancedMemory()
        
        self.initialized = True
        logger.info("Production workflow initialized successfully")
    
    async def shutdown(self):
        """关闭系统"""
        logger.info("Shutting down production workflow...")
        
        if self.agent_pool:
            await self.agent_pool.shutdown()
        
        if self.kernel:
            self.kernel.shutdown()
        
        self.initialized = False
        logger.info("Production workflow shutdown complete")
    
    async def process_request(self, user_id: str, request: str) -> str:
        """
        处理用户请求
        
        Args:
            user_id: 用户 ID
            request: 用户请求
            
        Returns:
            响应内容
        """
        # 1. 检查速率限制
        if not await self.rate_limiter.wait(user_id, timeout=5.0):
            return "请求频率过高，请稍后再试"
        
        # 2. 获取 Agent
        agent_def = AgentDefinition(
            name=f"Agent-{user_id}",
            role="assistant",
            goal=f"帮助用户 {user_id} 完成任务",
            backstory="你是专业的 AI 助手"
        )
        
        agent = await self.agent_pool.acquire(agent_def, timeout=10.0)
        
        try:
            # 3. 检查短期记忆
            recent = self.memory.search(user_id, limit=3)
            context = recent[0].content if recent else ""
            
            # 4. 处理请求 (简化)
            logger.info(f"Processing request for user {user_id}: {request[:50]}...")
            
            response = f"收到请求: {request}\n上下文: {context}"
            
            # 5. 保存到记忆
            self.memory.add(
                f"[{user_id}] {request} -> {response}",
                memory_type="short_term",
                importance=0.5,
                tags=[user_id]
            )
            
            # 6. 记录任务
            agent.increment_use()
            
            return response
            
        finally:
            # 7. 释放 Agent
            await self.agent_pool.release(agent)
    
    async def get_stats(self) -> dict:
        """获取系统统计"""
        return {
            "agent_pool": self.agent_pool.get_stats() if self.agent_pool else {},
            "rate_limiter": self.rate_limiter.get_stats("default") if self.rate_limiter else {},
            "memory": self.memory.get_stats() if self.memory else {},
            "kernel": self.kernel.get_stats() if self.kernel else {}
        }


async def main():
    """主函数"""
    workflow = ProductionWorkflow()
    
    try:
        # 初始化
        await workflow.initialize()
        
        # 处理请求
        responses = []
        for i in range(5):
            response = await workflow.process_request(
                user_id=f"user-{i % 2}",
                request=f"测试请求 {i}"
            )
            responses.append(response)
            print(f"Response {i}: {response[:50]}...")
        
        # 获取统计
        stats = await workflow.get_stats()
        print("\nSystem Stats:")
        print(f"Agent Pool: {stats['agent_pool']}")
        print(f"Rate Limiter: {stats['rate_limiter']}")
        
    finally:
        await workflow.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
