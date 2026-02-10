"""
PostgreSQL 集成示例

展示如何使用 PostgreSQL 作为存储后端：
1. 连接配置
2. 检查点存储
3. 审计日志
4. 向量搜索
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.types import StorageBackend


def demo_postgresql_connection():
    """演示 PostgreSQL 连接"""
    print("=" * 60)
    print("PostgreSQL 连接示例")
    print("=" * 60)
    
    # 方式 1: 直接配置
    kernel = AgentOSKernel(
        storage_backend=StorageBackend.POSTGRESQL,
        postgresql_host="localhost",
        postgresql_port=5432,
        postgresql_database="aosk",
        postgresql_user="aosk",
        postgresql_password="secret",
        table_prefix="aosk_"
    )
    
    # 验证连接
    try:
        stats = kernel.storage.get_stats()
        print(f"✅ 连接成功！")
        print(f"   后端: {stats['data'].backend if stats['data'] else 'unknown'}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    
    return kernel


def demo_checkpoints_with_postgres():
    """演示 PostgreSQL 检查点存储"""
    print("\n" + "=" * 60)
    print("PostgreSQL 检查点示例")
    print("=" * 60)
    
    kernel = AgentOSKernel(
        storage_backend=StorageBackend.POSTGRESQL,
        postgresql_host="localhost",
        postgresql_database="aosk"
    )
    
    # 创建 Agent
    pid = kernel.spawn_agent(name="CheckpointTest", task="Test checkpoint")
    print(f"✅ Agent 创建: {pid}")
    
    # 添加一些上下文
    for i in range(5):
        kernel.context_manager.add_page(
            agent_pid=pid,
            content=f"Memory page {i}: Some important content...",
            tokens=10,
            importance_score=0.5 + i * 0.1
        )
    
    # 创建检查点
    checkpoint_id = kernel.create_checkpoint(pid, "Test checkpoint")
    print(f"✅ 检查点创建: {checkpoint_id}")
    
    # 列出检查点
    checkpoints = kernel.storage.list_checkpoints(pid)
    print(f"\n检查点列表:")
    for cp in checkpoints:
        print(f"  - {cp.get('checkpoint_id', 'unknown')}: {cp.get('description', 'No description')}")
    
    # 从检查点恢复
    new_pid = kernel.restore_checkpoint(checkpoint_id)
    print(f"\n✅ 从检查点恢复: {new_pid}")
    
    return kernel


def demo_audit_logs_with_postgres():
    """演示 PostgreSQL 审计日志"""
    print("\n" + "=" * 60)
    print("PostgreSQL 审计日志示例")
    print("=" * 60)
    
    kernel = AgentOSKernel(
        storage_backend=StorageBackend.POSTGRESQL,
        postgresql_host="localhost",
        postgresql_database="aosk"
    )
    
    # 模拟一些操作
    operations = [
        {"action": "agent_spawn", "agent_pid": "agent_1", "resource": "kernel", "result": "success"},
        {"action": "tool_call", "agent_pid": "agent_1", "resource": "calculator", "result": "success"},
        {"action": "agent_spawn", "agent_pid": "agent_2", "resource": "kernel", "result": "success"},
        {"action": "tool_call", "agent_pid": "agent_2", "resource": "read_file", "result": "error", "details": {"path": "/etc/shadow"}},
        {"action": "checkpoint_create", "agent_pid": "agent_1", "resource": "storage", "result": "success"},
    ]
    
    for op in operations:
        kernel.storage.log_audit(op)
        print(f"✅ 记录审计日志: {op['action']} - {op['result']}")
    
    # 查询审计日志
    logs = kernel.storage.get_audit_logs(agent_pid="agent_1", limit=10)
    print(f"\nAgent 1 的审计日志 ({len(logs)} 条):")
    for log in logs:
        print(f"  - {log.get('action')}: {log.get('result')}")
    
    return kernel


def demo_vector_search_with_postgres():
    """演示 PostgreSQL 向量搜索"""
    print("\n" + "=" * 60)
    print("PostgreSQL 向量搜索示例")
    print("=" * 60)
    
    kernel = AgentOSKernel(
        storage_backend=StorageBackend.POSTGRESQL,
        postgresql_host="localhost",
        postgresql_database="aosk"
    )
    
    # 模拟向量数据 (384 维)
    import struct
    import random
    
    def random_embedding():
        """生成随机向量"""
        return struct.pack('96f', *[random.gauss(0, 1) for _ in range(96)])
    
    # 添加一些向量
    contents = [
        "Python 是一种高级编程语言",
        "机器学习是人工智能的子领域",
        "深度学习使用神经网络",
        "向量数据库存储嵌入向量",
        "PostgreSQL 是流行的关系数据库"
    ]
    
    for i, content in enumerate(contents):
        emb = random_embedding()
        kernel.storage.save_vector(
            key=f"doc_{i}",
            content=content,
            embedding=emb,
            metadata={"category": "documentation", "id": i}
        )
        print(f"✅ 保存向量: {content[:30]}...")
    
    # 搜索相似文档
    query = random_embedding()
    results = kernel.storage.search_vectors(query, top_k=3)
    
    print(f"\n搜索结果 (top 3):")
    for r in results:
        print(f"  - {r['content'][:40]}... (相似度: {r.get('similarity', 0):.3f})")
    
    return kernel


def demo_mixed_storage():
    """演示混合存储"""
    print("\n" + "=" * 60)
    print("混合存储示例")
    print("=" * 60)
    
    # PostgreSQL 用于持久化
    kernel = AgentOSKernel(
        storage_backend=StorageBackend.POSTGRESQL,
        postgresql_host="localhost",
        postgresql_database="aosk"
    )
    
    # 保存数据
    kernel.storage.save("test_key", {"message": "Hello from PostgreSQL!"})
    print("✅ 数据保存到 PostgreSQL")
    
    # 检索数据
    data = kernel.storage.retrieve("test_key")
    print(f"✅ 数据检索: {data}")
    
    # 审计日志
    kernel.storage.log_audit({
        "action": "test_operation",
        "agent_pid": "test",
        "resource": "test",
        "result": "success"
    })
    print("✅ 审计日志已记录")
    
    # 检查点
    pid = kernel.spawn_agent(name="TestAgent", task="Testing")
    cp_id = kernel.create_checkpoint(pid, "Test checkpoint")
    print(f"✅ 检查点已创建: {cp_id}")


def demo_postgresql_connection_pool():
    """演示连接池配置"""
    print("\n" + "=" * 60)
    print("连接池配置示例")
    print("=" * 60)
    
    kernel = AgentOSKernel(
        storage_backend=StorageBackend.POSTGRESQL,
        postgresql_host="localhost",
        postgresql_database="aosk",
        postgresql_pool_size=20,      # 最小连接数
        postgresql_max_overflow=40    # 最大额外连接
    )
    
    print("✅ 连接池配置:")
    print("   最小连接数: 20")
    print("   最大连接数: 60 (20 + 40)")
    print("   连接池已就绪")


if __name__ == "__main__":
    import random
    
    print("\n🚀 Agent-OS-Kernel PostgreSQL 集成示例")
    print("=" * 60)
    
    try:
        demo_postgresql_connection()
        demo_checkpoints_with_postgres()
        demo_audit_logs_with_postgres()
        demo_vector_search_with_postgres()
        demo_mixed_storage()
        demo_postgresql_connection_pool()
        
        print("\n" + "=" * 60)
        print("✅ 所有示例完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n请确保 PostgreSQL 已安装并运行:")
        print("  1. 安装 PostgreSQL: sudo apt install postgresql-15")
        print("  2. 创建数据库: CREATE DATABASE aosk;")
        print("  3. 创建用户并授权")
        print("  4. 更新连接配置")
