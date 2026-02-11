#!/usr/bin/env python3
"""Storage 使用示例"""

from agent_os_kernel.core.storage import StorageManager


def main():
    print("="*50)
    print("Storage 示例")
    print("="*50)
    
    # 1. 创建存储
    print("\n1. 创建存储")
    
    storage = StorageManager()
    print("   ✓ 存储管理器创建成功")
    
    # 2. 保存数据
    print("\n2. 保存数据")
    
    storage.save("user/001", {"name": "Alice", "age": 30})
    storage.save("user/002", {"name": "Bob", "age": 25})
    storage.save("session/active", {"count": 5})
    
    print("   ✓ 保存3条数据")
    
    # 3. 获取数据
    print("\n3. 获取数据")
    
    user = storage.retrieve("user/001")
    print(f"   用户: {user}")
    
    # 4. 检查存在
    print("\n4. 检查存在")
    
    exists = storage.exists("user/001")
    print(f"   user/001 存在: {exists}")
    
    # 5. 统计
    print("\n5. 获取统计")
    
    print(f"   ✓ 存储就绪")
    
    # 6. 删除
    print("\n6. 删除数据")
    
    storage.delete("user/002")
    exists = storage.exists("user/002")
    print(f"   user/002 存在: {exists}")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    main()
