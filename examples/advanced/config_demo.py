# -*- coding: utf-8 -*-
"""配置管理器演示"""

import asyncio
from agent_os_kernel.core.config_manager import ConfigManager


async def main():
    print("="*60)
    print("Config Manager Demo")
    print("="*60)
    
    # 创建配置管理器
    manager = ConfigManager(config_dir="config", enable_hot_reload=True)
    await manager.initialize()
    
    print("\n📁 配置文件演示")
    
    # 模拟创建配置
    import yaml
    import os
    os.makedirs("config", exist_ok=True)
    
    with open("config/app.yaml", "w") as f:
        yaml.dump({
            "app": {
                "name": "AgentOSKernel",
                "version": "1.0.0"
            },
            "database": {
                "host": "localhost",
                "port": 5432
            }
        }, f)
    
    # 加载配置
    await manager.load("app")
    
    # 获取配置
    print(f"\n📄 应用名称: {await manager.get('app', 'app/name')}")
    print(f"📄 数据库端口: {await manager.get('app', 'database/port')}")
    
    # 动态修改配置
    await manager.set("app", "app/debug", True)
    print(f"📄 Debug 模式: {await manager.get('app', 'app/debug')}")
    
    # 统计
    stats = manager.get_stats()
    print(f"\n📊 配置统计: {stats}")
    
    # 清理
    os.remove("config/app.yaml")
    
    await manager.shutdown()
    print("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(main())
