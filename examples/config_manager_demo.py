#!/usr/bin/env python3
"""ConfigManager 使用示例

演示配置热加载功能。
"""

import asyncio
import tempfile
import os
from agent_os_kernel.core.config_manager import ConfigManager


async def main():
    print("="*50)
    print("ConfigManager 示例")
    print("="*50)
    
    # 1. 创建临时配置
    print("\n1. 创建临时配置")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("database:\n  host: localhost\n  port: 5432\n")
        f.write("debug: true\n")
        config_path = f.name
    
    print(f"   配置文件: {config_path}")
    
    # 2. 创建管理器
    print("\n2. 创建配置管理器")
    
    cm = ConfigManager(config_dir=tempfile.gettempdir(), enable_hot_reload=False)
    print("   ✓ 管理器创建成功")
    
    # 3. 加载配置
    print("\n3. 加载配置")
    
    await cm.load("temp", config_path)
    value = await cm.get("temp", "debug")
    print(f"   debug: {value}")
    
    # 4. 设置配置
    print("\n4. 设置配置")
    
    await cm.set("temp", "new_key", "new_value")
    value = await cm.get("temp", "new_key")
    print(f"   new_key: {value}")
    
    # 5. 统计
    print("\n6. 获取统计")
    
    stats = cm.get_stats()
    print(f"   总配置数: {stats['total_configs']}")
    
    # 清理
    os.unlink(config_path)
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
