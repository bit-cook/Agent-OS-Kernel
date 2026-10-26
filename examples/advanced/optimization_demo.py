"""
性能优化示例

展示上下文压缩、缓存和批量处理的使用。

功能：
1. Context Compressor - 上下文压缩
2. Tiered Cache - 多层缓存
3. Batch Processor - 批量处理
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel.core.optimization.compressor import (
    ContextCompressor, CompressionStrategy, CompressionConfig, compress_context
)
from agent_os_kernel.core.optimization.cache import TieredCache, CachePolicy
from agent_os_kernel.core.optimization.batch import (
    BatchProcessor, BatchStrategy, BatchConfig, create_batch_processor
)


async def demo_context_compression():
    """上下文压缩示例"""
    print("=" * 60)
    print("上下文压缩示例")
    print("=" * 60)

    # 创建压缩器（max_tokens 设小一些，以便触发压缩）
    config = CompressionConfig(
        max_tokens=120,
        preserve_system_prompt=True,
        preserve_recent=3,
        importance_threshold=0.5
    )
    compressor = ContextCompressor(config)

    # 模拟长对话
    messages = []

    # 系统提示
    messages.append({
        "role": "system",
        "content": "你是一个专业的数据分析助手，帮助用户分析数据并提供洞察。"
    })

    # 历史消息 (20 条)
    for i in range(20):
        messages.append({
            "role": "user",
            "content": f"用户第 {i+1} 个问题：关于数据分析的详细问题，内容很多，包含大量的背景信息和具体需求，需要仔细分析才能给出准确的答案。"
        })
        messages.append({
            "role": "assistant",
            "content": f"助手回复第 {i+1} 条：这是一个详细的分析结果，包含了数据处理的步骤、统计方法的说明、结论的推导过程，以及对用户需求的完整回应。"
        })

    # 最近消息
    messages.append({
        "role": "user",
        "content": "总结一下所有的分析结果"
    })

    original_tokens = compressor.get_compression_report(messages, messages)["original_tokens"]
    print(f"\n📊 原始消息: {len(messages)} 条")
    print(f"   压缩前 tokens: ~{original_tokens}")

    # 测试不同策略
    strategies = [
        CompressionStrategy.TRUNCATE,
        CompressionStrategy.SUMMARIZE,
        CompressionStrategy.IMPORTANCE_FILTER,
        CompressionStrategy.HYBRID
    ]

    for strategy in strategies:
        print(f"\n🔧 策略: {strategy.value}")
        try:
            compressed = compressor.compress_messages(messages, strategy)
        except Exception as e:
            # 内核已知缺陷：importance 策略收尾排序的 key 返回消息 dict 而非序号，
            # 保留 2 条以上消息时必崩（examples 无法修复，仅如实呈现）
            print(f"   ⚠️ 该策略在当前内核版本无法完成: {type(e).__name__}: {e}")
            continue

        report = compressor.get_compression_report(messages, compressed)
        print(f"   压缩后: {len(compressed)} 条消息")
        print(f"   压缩率: {report['compression_ratio']:.1%}")
        print(f"   节省: {report['saved_tokens']} tokens")

    return compressor


async def demo_tiered_cache():
    """多层缓存示例"""
    print("\n" + "=" * 60)
    print("多层缓存示例")
    print("=" * 60)

    # 创建缓存
    policy = CachePolicy(
        max_memory_mb=10,
        max_disk_mb=100,
        default_ttl_seconds=300
    )
    cache = TieredCache(policy)

    # 测试数据
    test_data = {
        "user_id": 12345,
        "name": "测试用户",
        "preferences": {"theme": "dark", "language": "zh-CN"},
        "history": [f"item_{i}" for i in range(100)]
    }

    # 设置缓存
    print("\n📝 设置缓存...")
    cache.set("user:12345", test_data, ttl_seconds=60)
    cache.set("session:abc", {"active": True}, ttl_seconds=30)
    cache.set("config:theme", "dark", ttl_seconds=300)

    # 获取缓存
    print("\n📖 获取缓存...")
    value, level = cache.get("user:12345")
    print(f"   用户数据: {value['name']} (来源: {level.value})")

    value, level = cache.get("session:abc")
    print(f"   会话状态: {value} (来源: {level.value})")

    # 获取统计
    print("\n📊 缓存统计:")
    stats = cache.stats()
    print(f"   内存: {stats['memory']['items']} 项, {stats['memory']['size_mb']:.2f} MB")
    print(f"   磁盘: {stats['disk']['size_mb']:.2f} MB")

    # 测试过期
    print("\n⏰ 测试缓存过期...")
    cache.set("temp:test", {"key": "value"}, ttl_seconds=1)
    value, _ = cache.get("temp:test")
    print(f"   1秒内: {value}")

    await asyncio.sleep(1.1)
    value, _ = cache.get("temp:test")
    print(f"   1秒后: {value}")

    return cache


async def demo_batch_processor():
    """批量处理示例"""
    print("\n" + "=" * 60)
    print("批量处理示例")
    print("=" * 60)

    # 创建批量处理器
    config = BatchConfig(
        max_batch_size=5,
        max_concurrent=3,
        retry_count=2
    )
    processor = BatchProcessor(config)

    # 模拟处理函数
    async def process_item(item):
        # 模拟 API 调用延迟
        await asyncio.sleep(0.1)
        return {"processed": True, "item": item, "time": asyncio.get_event_loop().time()}

    # 添加批量任务
    print("\n📝 添加批量任务...")
    items = [
        {"data": f"task_{i}", "priority": 5 - i}
        for i in range(10)
    ]

    item_ids = await processor.add_batch(items)
    print(f"   添加了 {len(item_ids)} 个任务")

    # 处理（每次最多处理 max_batch_size 个，循环直到队列清空）
    print("\n🚀 处理批量任务...")
    results = []
    while True:
        batch_results = await processor.process(process_item, BatchStrategy.ADAPTIVE)
        if not batch_results:
            break
        results.extend(batch_results)

    success_count = sum(1 for r in results if r.success)
    print(f"   成功: {success_count}/{len(results)}")

    # 显示结果
    print("\n📊 处理结果:")
    for result in results[:5]:
        status = "✅" if result.success else "❌"
        item = result.result.get('item', 'N/A') if result.result else 'N/A'
        print(f"   {status} {result.item_id}: {item}")

    # 统计
    print("\n📈 处理器统计:")
    stats = processor.stats()
    print(f"   队列大小: {stats['queue_size']}")
    print(f"   最大批量: {stats['max_batch_size']}")
    print(f"   最大并发: {stats['max_concurrent']}")

    return processor


async def demo_optimization_pipeline():
    """完整优化流水线示例"""
    print("\n" + "=" * 60)
    print("完整优化流水线")
    print("=" * 60)

    # 1. 创建组件
    compressor = ContextCompressor(CompressionConfig(max_tokens=300))
    cache = TieredCache()
    batch_processor = create_batch_processor(max_batch_size=5)

    # 2. 模拟 Agent 对话流
    conversation = [
        {"role": "system", "content": "你是一个有帮助的助手。"},
    ]

    # 添加 50 条历史消息
    for i in range(50):
        conversation.append({
            "role": "user",
            "content": f"用户消息 {i+1}: 这是一个测试消息，包含一些内容。"
        })
        conversation.append({
            "role": "assistant",
            "content": f"助手回复 {i+1}: 这是对应的回复，包含有用的信息。"
        })

    # 添加最后一条消息
    conversation.append({
        "role": "user",
        "content": "总结所有对话"
    })

    print(f"\n📊 原始对话: {len(conversation)} 条消息")

    # 3. 压缩上下文
    print("\n🔧 步骤1: 压缩上下文...")
    compressed = compressor.compress_messages(conversation, CompressionStrategy.HYBRID)
    report = compressor.get_compression_report(conversation, compressed)

    print(f"   压缩后: {len(compressed)} 条消息")
    print(f"   节省: {report['saved_tokens']} tokens ({report['compression_ratio']:.1%})")

    # 4. 批量处理请求
    print("\n🚀 步骤2: 批量处理...")

    async def generate_response(message):
        await asyncio.sleep(0.05)
        return {"response": f"处理: {message[:30]}..."}

    batch_items = [
        {"data": msg.get("content", "")}
        for msg in compressed[-5:]
    ]

    await batch_processor.add_batch(batch_items)
    results = []
    while True:
        batch_results = await batch_processor.process(generate_response)
        if not batch_results:
            break
        results.extend(batch_results)

    success = sum(1 for r in results if r.success)
    print(f"   批量处理: {success}/{len(results)} 成功")

    # 5. 缓存结果
    print("\n💾 步骤3: 缓存结果...")
    cache.set("conversation:summary", {
        "compressed_messages": len(compressed),
        "result": "处理完成"
    }, ttl_seconds=3600)

    value, level = cache.get("conversation:summary")
    print(f"   缓存: {value} (来源: {level.value})")

    return {
        "compressor": compressor,
        "cache": cache,
        "batch_processor": batch_processor
    }


async def demo_chinese_optimization():
    """中文优化示例"""
    print("\n" + "=" * 60)
    print("中文场景优化")
    print("=" * 60)

    # 中文消息
    messages = [
        {"role": "system", "content": "你是一个专业的AI助手。"},
    ]

    # 添加中文对话
    for i in range(15):
        messages.append({
            "role": "user",
            "content": f"用户{i+1}：请问关于机器学习的问题，我想了解深度学习的发展历程和应用场景，以及最新的研究进展。"
        })
        messages.append({
            "role": "assistant",
            "content": f"助手{i+1}：关于深度学习，这是近年来人工智能领域最重要的技术突破之一。深度神经网络在图像识别、自然语言处理、语音识别等任务上都取得了突破性的进展。"
        })

    messages.append({
        "role": "user",
        "content": "总结一下深度学习的关键点"
    })

    print(f"\n📊 中文对话: {len(messages)} 条")

    # 使用混合策略压缩
    compressor = ContextCompressor(CompressionConfig(max_tokens=200))
    compressed = compressor.compress_messages(messages, CompressionStrategy.HYBRID)
    report = compressor.get_compression_report(messages, compressed)

    print(f"\n🔧 压缩结果:")
    print(f"   原始: {len(messages)} 条")
    print(f"   压缩后: {len(compressed)} 条")
    print(f"   压缩率: {report['compression_ratio']:.1%}")

    # 显示摘要
    for msg in compressed:
        if msg.get("_compressed"):
            print(f"\n📝 生成的摘要:")
            print(f"   {msg['content'][:150]}...")

    # 便捷函数：compress_context
    quick = compress_context(messages, max_tokens=200, strategy="hybrid")
    print(f"\n⚡ 便捷函数 compress_context: {len(messages)} -> {len(quick)} 条")

    return compressor


async def main():
    """主函数"""
    print("\n🚀 性能优化示例")
    print("=" * 60)

    # 1. 上下文压缩
    await demo_context_compression()

    # 2. 多层缓存
    await demo_tiered_cache()

    # 3. 批量处理
    await demo_batch_processor()

    # 4. 完整流水线
    await demo_optimization_pipeline()

    # 5. 中文优化
    await demo_chinese_optimization()

    print("\n" + "=" * 60)
    print("✅ 所有示例完成!")
    print("=" * 60)

    print("\n📚 进一步阅读:")
    print("   - Context Engineering: https://manus.im/blog/context-engineering")
    print("   - AutoGen Documentation: https://microsoft.github.io/autogen/")


if __name__ == "__main__":
    asyncio.run(main())
