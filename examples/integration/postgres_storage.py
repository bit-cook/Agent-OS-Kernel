"""
PostgreSQL 存储示例

演示如何使用 PostgreSQL 作为存储后端
"""

import sys
sys.path.insert(0, '..')

from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.storage import StorageManager


def demo_postgres_storage():
    """使用 PostgreSQL 存储的示例"""
    print("=" * 60)
    print("PostgreSQL 存储示例")
    print("=" * 60)
    print()
    
    # 数据库连接字符串
    # 格式: postgresql://username:password@host:port/database
    connection_string = "postgresql://postgres:password@localhost:5432/agent_os"
    
    print(f"连接到: {connection_string}")
    print()
    
    try:
        # 创建 PostgreSQL 存储
        storage = StorageManager.from_postgresql(connection_string)
        
        # 创建内核，使用 PostgreSQL 存储
        kernel = AgentOSKernel(storage_backend=storage.backend)
        
        print("✓ 成功连接到 PostgreSQL")
        print()
        
        # 创建 Agent
        agent_pid = kernel.spawn_agent(
            name="PersistentAgent",
            task="Demonstrate persistent storage",
            priority=30
        )
        
        # 运行几步
        print("运行 Agent...")
        kernel.run(max_iterations=3)
        
        # 创建检查点
        checkpoint_id = kernel.create_checkpoint(agent_pid, "Demo checkpoint")
        print(f"\n检查点已保存: {checkpoint_id}")
        
        # 显示存储统计
        stats = storage.get_stats()
        print(f"\n存储统计:")
        print(f"  进程: {stats['processes']}")
        print(f"  检查点: {stats['checkpoints']}")
        print(f"  审计日志: {stats['audit_logs']}")
        
        # 查看审计追踪
        audit_trail = kernel.get_audit_trail(agent_pid, limit=10)
        print(f"\n审计日志条目: {len(audit_trail)}")
        
        kernel.shutdown()
        
        print("\n✓ 示例完成")
        print("\n注意: 数据已持久化到 PostgreSQL，")
        print("     即使程序重启也可以恢复。")
        
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("\n请安装 PostgreSQL 依赖:")
        print("  pip install psycopg2-binary pgvector")
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        print("\n请确保:")
        print("  1. PostgreSQL 服务器正在运行")
        print("  2. 数据库已创建")
        print("  3. 连接字符串正确")
        print("\n创建数据库:")
        print("  createdb agent_os")
        print("\n或者使用内存存储进行测试:")
        print("  kernel = AgentOSKernel()  # 不使用 PostgreSQL")


if __name__ == "__main__":
    demo_postgres_storage()
