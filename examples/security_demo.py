"""
Agent-OS-Kernel 安全策略演示

展示安全策略的使用方法
"""

from agent_os_kernel.core.security import SecurityPolicy, PermissionLevel


def demo_security():
    """演示安全策略"""
    print("=" * 60)
    print("Agent-OS-Kernel 安全策略演示")
    print("=" * 60)
    
    # 创建安全策略
    policy = SecurityPolicy()
    
    # 检查权限
    print("\n权限检查:")
    print(f"  NONE: {PermissionLevel.NONE.value}")
    print(f"  READ: {PermissionLevel.READ.value}")
    print(f"  WRITE: {PermissionLevel.WRITE.value}")
    print(f"  ADMIN: {PermissionLevel.ADMIN.value}")
    
    # 安全策略初始化
    print(f"\n✅ 安全策略创建成功")
    print(f"   策略启用: {policy.is_enabled}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_security()
