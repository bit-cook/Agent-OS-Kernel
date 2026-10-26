"""
Agent-OS-Kernel 安全策略演示

展示安全策略的使用方法
"""

from agent_os_kernel.core.security import (
    PermissionLevel,
    PermissionManager,
    SecurityPolicy,
)


def demo_security():
    """演示安全策略"""
    print("=" * 60)
    print("Agent-OS-Kernel 安全策略演示")
    print("=" * 60)

    # 权限级别
    print("\n权限级别 (PermissionLevel):")
    for level in (
        PermissionLevel.RESTRICTED,
        PermissionLevel.STANDARD,
        PermissionLevel.ELEVATED,
        PermissionLevel.ADMIN,
    ):
        print(f"  {level.name}: {level.value}")

    # 创建安全策略（默认 STANDARD）
    policy = SecurityPolicy()
    print(f"\n✅ 默认安全策略创建成功")
    print(f"   权限级别: {policy.permission_level.value}")
    print(f"   只读模式: {policy.read_only}")
    print(f"   网络访问: {policy.network_enabled}")
    print(f"   内存上限: {policy.max_memory_mb} MB")
    print(f"   CPU 上限: {policy.max_cpu_percent}%")
    print(f"   执行超时: {policy.max_execution_time} 秒")

    # 自定义受限策略
    restricted = SecurityPolicy(
        permission_level=PermissionLevel.RESTRICTED,
        read_only=True,
        network_enabled=False,
        max_memory_mb=256,
        max_cpu_percent=25,
        max_execution_time=60,
        allowed_tools=["read_file", "search"],
        blocked_tools=["shell_exec"],
    )
    print(f"\n✅ 受限策略创建成功")
    print(f"   权限级别: {restricted.permission_level.value}")
    print(f"   允许的工具: {restricted.allowed_tools}")
    print(f"   禁用的工具: {restricted.blocked_tools}")

    # 权限管理器
    manager = PermissionManager()
    agent_pid = "agent-001"

    manager.set_policy(agent_pid, restricted)
    print(f"\n权限检查 (Agent: {agent_pid}):")
    for tool in ("read_file", "shell_exec", "search"):
        allowed = manager.can_use_tool(agent_pid, tool)
        print(f"  工具 {tool}: {'✅ 允许' if allowed else '❌ 拒绝'}")

    for host in ("example.com", "evil.com"):
        allowed = manager.can_access_network(agent_pid, host)
        print(f"  访问 {host}: {'✅ 允许' if allowed else '❌ 拒绝'}")

    ok, reason = manager.check_resource_limits(agent_pid, memory_mb=128, execution_time=30)
    print(f"  资源限额 (128MB/30s): {'✅' if ok else '❌'} {reason}")
    ok, reason = manager.check_resource_limits(agent_pid, memory_mb=1024, execution_time=30)
    print(f"  资源限额 (1024MB/30s): {'✅' if ok else '❌'} {reason}")

    # 策略导出
    print(f"\n策略导出 (to_dict):")
    for key, value in restricted.to_dict().items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_security()
