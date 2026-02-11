#!/usr/bin/env python3
"""PluginSystem 使用示例"""

from agent_os_kernel.core.plugin_system import (
    PluginManager, PluginState, BasePlugin
)


def main():
    print("="*50)
    print("PluginSystem 示例")
    print("="*50)
    
    # 1. 创建插件管理器
    print("\n1. 创建插件管理器")
    
    pm = PluginManager()
    print("   ✓ 插件管理器创建成功")
    
    # 2. 获取统计
    print("\n2. 获取统计")
    
    stats = pm.get_stats()
    print(f"   总插件数: {stats['total_plugins']}")
    print(f"   已加载: {stats['loaded']}")
    print(f"   已启用: {stats['enabled']}")
    
    # 3. 列出插件
    print("\n3. 列出插件")
    
    plugins = pm.list_plugins()
    print(f"   插件数: {len(plugins)}")
    
    # 4. 列出已加载
    print("\n4. 列出已加载")
    
    loaded = pm.list_loaded()
    print(f"   已加载插件: {len(loaded)}")
    
    # 5. 测试插件状态
    print("\n5. 插件状态")
    
    print(f"   UNLOADED: {PluginState.UNLOADED.value}")
    print(f"   LOADED: {PluginState.LOADED.value}")
    print(f"   ENABLED: {PluginState.ENABLED.value}")
    print(f"   DISABLED: {PluginState.DISABLED.value}")
    print(f"   ERROR: {PluginState.ERROR.value}")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    main()
