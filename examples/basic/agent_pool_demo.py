#!/usr/bin/env python3
"""AgentPool 使用示例

演示Agent对象池的管理。
"""

import asyncio
from agent_os_kernel.core.agent_pool import AgentPool


async def main():
    print("="*50)
    print("AgentPool 示例")
    print("="*50)
    
    # 1. 创建池
    print("\n1. 创建Agent池")
    
    pool = AgentPool(max_size=3, idle_timeout=60)
    await pool.initialize()
    
    print(f"   最大大小: {pool.max_size}")
    print(f"   空闲超时: {pool.idle_timeout}秒")
    
    # 2. 统计
    print("\n2. 获取统计")
    
    stats = pool.get_stats()
    print(f"   总Agent: {stats['total_agents']}")
    print(f"   空闲Agent: {stats['idle_agents']}")
    print(f"   忙碌Agent: {stats['busy_agents']}")
    
    # 3. 获取活跃列表
    print("\n3. 获取活跃列表")
    
    agents = pool.get_active_agents()
    print(f"   活跃Agent数: {len(agents)}")
    
    # 4. 关闭
    print("\n4. 关闭池")
    
    await pool.shutdown()
    print("   ✓ 池已关闭")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
