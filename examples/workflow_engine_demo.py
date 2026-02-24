# -*- coding: utf-8 -*-
"""
工作流引擎示例演示

演示工作流定义、任务依赖、并行执行和错误处理等功能。
"""

import asyncio
import sys
sys.path.insert(0, '/root/.openclaw/workspace')

from agent_os_kernel.core.workflow_engine import (
    WorkflowEngine,
    Workflow,
    Task,
    TaskConfig,
    TaskStatus,
    WorkflowStatus,
)


def print_section(title):
    """打印分隔标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(result):
    """打印执行结果"""
    print(f"\n工作流状态: {result.status.value}")
    print(f"执行时间: {result.end_time - result.start_time:.3f}s")
    
    if result.error:
        print(f"错误: {result.error}")
    
    print("\n任务结果:")
    for task_id, task_result in result.results.items():
        status_symbol = {
            TaskStatus.COMPLETED: "✓",
            TaskStatus.FAILED: "✗",
            TaskStatus.SKIPPED: "⊘",
            TaskStatus.RUNNING: "⟳",
            TaskStatus.PENDING: "○",
        }.get(task_result.status, "?")
        
        print(f"  {status_symbol} {task_id}: {task_result.status.value}")
        if task_result.result is not None:
            print(f"      结果: {task_result.result}")
        if task_result.error:
            print(f"      错误: {task_result.error}")


# 示例1: 简单线性工作流
def demo_simple_linear_workflow():
    """演示简单线性工作流"""
    print_section("示例1: 简单线性工作流")
    
    engine = WorkflowEngine()
    workflow = engine.create_workflow("simple_linear", "简单线性工作流")
    
    def step1(input_data, context):
        print("  → 执行步骤1: 数据加载")
        return {"data": [1, 2, 3, 4, 5]}
    
    def step2(input_data, context):
        print("  → 执行步骤2: 数据处理")
        return {"sum": sum(input_data.get("data", []))}
    
    def step3(input_data, context):
        print("  → 执行步骤3: 结果输出")
        return f"结果: {input_data.get('sum', 0)}"
    
    # 添加任务
    workflow.add_task(Task(TaskConfig(task_id="load_data", func=step1, dependencies=[])))
    workflow.add_task(Task(TaskConfig(task_id="process_data", func=step2, dependencies=["load_data"])))
    workflow.add_task(Task(TaskConfig(task_id="output_result", func=step3, dependencies=["process_data"])))
    
    # 运行工作流
    result = engine.run_sync("simple_linear")
    print_result(result)


# 示例2: 并行工作流
def demo_parallel_workflow():
    """演示并行工作流"""
    print_section("示例2: 并行工作流")
    
    engine = WorkflowEngine()
    workflow = engine.create_workflow("parallel_demo", "并行处理工作流")
    
    def fetch_from_api_a(input_data, context):
        import time
        print("  → API A 数据获取...")
        time.sleep(0.2)
        return {"api_a": "数据A"}
    
    def fetch_from_api_b(input_data, context):
        import time
        print("  → API B 数据获取...")
        time.sleep(0.3)
        return {"api_b": "数据B"}
    
    def fetch_from_db(input_data, context):
        import time
        print("  → 数据库查询...")
        time.sleep(0.1)
        return {"db": "数据库数据"}
    
    def aggregate_data(input_data, context):
        print("  → 数据聚合...")
        results = {}
        for task_id, result in input_data.items():
            if hasattr(result, 'result'):
                results.update(result.result if isinstance(result.result, dict) else {task_id: result.result})
        return results
    
    # 添加并行任务
    workflow.add_task(Task(TaskConfig(
        task_id="api_a", 
        func=fetch_from_api_a, 
        dependencies=[],
        parallel=True
    )))
    workflow.add_task(Task(TaskConfig(
        task_id="api_b", 
        func=fetch_from_api_b, 
        dependencies=[],
        parallel=True
    )))
    workflow.add_task(Task(TaskConfig(
        task_id="db_query", 
        func=fetch_from_db, 
        dependencies=[],
        parallel=True
    )))
    
    # 聚合任务（等待所有并行任务完成）
    workflow.add_task(Task(TaskConfig(
        task_id="aggregate", 
        func=aggregate_data, 
        dependencies=["api_a", "api_b", "db_query"]
    )))
    
    result = engine.run_sync("parallel_demo")
    print_result(result)


# 示例3: 条件执行工作流
def demo_conditional_workflow():
    """演示条件执行工作流"""
    print_section("示例3: 条件执行工作流")
    
    engine = WorkflowEngine()
    workflow = engine.create_workflow("conditional_demo", "条件判断工作流")
    
    def generate_random_value(input_data, context):
        import random
        value = random.randint(1, 100)
        print(f"  → 生成随机值: {value}")
        return {"value": value}
    
    def process_high_value(input_data, context):
        print("  → 处理高值 (>50)")
        return {"processed": "高优先级处理"}
    
    def process_low_value(input_data, context):
        print("  → 处理低值 (≤50)")
        return {"processed": "低优先级处理"}
    
    # 高值处理条件
    def is_high_value(results):
        task1_result = results.get("generate", TaskResult("generate", TaskStatus.PENDING))
        return task1_result.result.get("value", 0) > 50
    
    # 低值处理条件
    def is_low_value(results):
        task1_result = results.get("generate", TaskResult("generate", TaskStatus.PENDING))
        return task1_result.result.get("value", 0) <= 50
    
    workflow.add_task(Task(TaskConfig(
        task_id="generate", 
        func=generate_random_value, 
        dependencies=[]
    )))
    workflow.add_task(Task(TaskConfig(
        task_id="high_process", 
        func=process_high_value, 
        dependencies=["generate"],
        condition=is_high_value
    )))
    workflow.add_task(Task(TaskConfig(
        task_id="low_process", 
        func=process_low_value, 
        dependencies=["generate"],
        condition=is_low_value
    )))
    
    result = engine.run_sync("conditional_demo")
    print_result(result)
    
    # 根据结果确定哪个分支执行了
    if result.results.get("high_process", TaskResult("", TaskStatus.PENDING)).status == TaskStatus.COMPLETED:
        print("\n分支: 执行了高值处理")
    else:
        print("\n分支: 执行了低值处理")


# 示例4: 错误处理和重试
def demo_error_handling():
    """演示错误处理和重试"""
    print_section("示例4: 错误处理和重试")
    
    engine = WorkflowEngine()
    workflow = engine.create_workflow("error_handling_demo", "错误处理工作流")
    
    attempt_count = {"counter": 0}
    
    def unstable_service(input_data, context):
        """不稳定的模拟服务"""
        attempt_count["counter"] += 1
        print(f"  → 服务调用尝试 #{attempt_count['counter']}")
        
        # 前两次失败，第三次成功
        if attempt_count["counter"] < 3:
            raise ConnectionError("网络连接失败")
        return {"status": "成功连接"}
    
    def fallback_service(input_data, context):
        print("  → 使用备用服务")
        return {"status": "备用服务响应"}
    
    def process_result(input_data, context):
        print("  → 处理最终结果")
        return "处理完成"
    
    workflow.add_task(Task(TaskConfig(
        task_id="unstable_service",
        func=unstable_service,
        dependencies=[],
        retry_count=3,
        retry_delay=0.1
    )))
    workflow.add_task(Task(TaskConfig(
        task_id="fallback",
        func=fallback_service,
        dependencies=["unstable_service"],
        condition=lambda r: r.get("unstable_service", TaskResult("", TaskStatus.PENDING)).status == TaskStatus.FAILED
    )))
    workflow.add_task(Task(TaskConfig(
        task_id="final_process",
        func=process_result,
        dependencies=["unstable_service", "fallback"],
        condition=lambda r: (
            r.get("unstable_service", TaskResult("", TaskStatus.PENDING)).status == TaskStatus.COMPLETED or
            r.get("fallback", TaskResult("", TaskStatus.PENDING)).status == TaskStatus.COMPLETED
        )
    )))
    
    result = engine.run_sync("error_handling_demo")
    print_result(result)


# 示例5: 完整的数据处理管道
def demo_data_pipeline():
    """演示完整的数据处理管道"""
    print_section("示例5: 数据处理管道")
    
    engine = WorkflowEngine()
    workflow = engine.create_workflow("data_pipeline", "ETL数据管道")
    
    def extract_from_source(input_data, context):
        print("  → 数据抽取: 读取源数据")
        return {
            "raw_data": [
                {"id": 1, "name": "产品A", "price": 100},
                {"id": 2, "name": "产品B", "price": 200},
                {"id": 3, "name": "产品C", "price": 150},
            ]
        }
    
    def transform_data(input_data, context):
        print("  → 数据转换: 应用业务规则")
        raw = input_data.get("extract", {}).get("raw_data", [])
        transformed = []
        for item in raw:
            transformed.append({
                **item,
                "price_with_tax": item["price"] * 1.1,
                "category": "Electronics"
            })
        return {"transformed_data": transformed}
    
    def validate_data(input_data, context):
        print("  → 数据验证: 检查数据质量")
        transformed = input_data.get("transform", {}).get("transformed_data", [])
        
        errors = []
        for item in transformed:
            if item.get("price", 0) <= 0:
                errors.append(f"无效价格: {item}")
        
        return {
            "is_valid": len(errors) == 0,
            "error_count": len(errors),
            "records_count": len(transformed)
        }
    
    def load_to_destination(input_data, context):
        print("  → 数据加载: 写入目标系统")
        transformed = input_data.get("transform", {}).get("transformed_data", [])
        validation = input_data.get("validate", {})
        
        if validation.get("is_valid", False):
            return {
                "loaded": len(transformed),
                "status": "成功加载",
                "summary": f"加载了 {len(transformed)} 条记录"
            }
        else:
            return {
                "loaded": 0,
                "status": "验证失败",
                "summary": f"发现 {validation.get('error_count', 0)} 个错误"
            }
    
    def generate_report(input_data, context):
        print("  → 生成报告")
        load_result = input_data.get("load", {})
        return {
            "report": f"ETL完成 - {load_result.get('summary', '未知')}"
        }
    
    # 构建工作流DAG
    workflow.add_task(Task(TaskConfig(
        task_id="extract",
        func=extract_from_source,
        dependencies=[]
    )))
    workflow.add_task(Task(TaskConfig(
        task_id="transform",
        func=transform_data,
        dependencies=["extract"]
    )))
    workflow.add_task(Task(TaskConfig(
        task_id="validate",
        func=validate_data,
        dependencies=["transform"]
    )))
    workflow.add_task(Task(TaskConfig(
        task_id="load",
        func=load_to_destination,
        dependencies=["validate"]
    )))
    workflow.add_task(Task(TaskConfig(
        task_id="report",
        func=generate_report,
        dependencies=["load"]
    )))
    
    result = engine.run_sync("data_pipeline")
    print_result(result)


# 异步版本示例
async def demo_async_workflow():
    """演示异步工作流"""
    print_section("异步工作流示例")
    
    engine = WorkflowEngine()
    workflow = engine.create_workflow("async_demo", "异步工作流")
    
    async def async_task_1(input_data, context):
        print("  → 异步任务1: 加载数据")
        await asyncio.sleep(0.2)
        return {"async_data": "任务1数据"}
    
    async def async_task_2(input_data, context):
        print("  → 异步任务2: 处理数据")
        await asyncio.sleep(0.15)
        return {"processed": "任务2处理结果"}
    
    async def async_task_3(input_data, context):
        print("  → 异步任务3: 保存结果")
        await asyncio.sleep(0.1)
        return {"saved": True}
    
    workflow.add_task(Task(TaskConfig(task_id="async1", func=async_task_1, dependencies=[])))
    workflow.add_task(Task(TaskConfig(task_id="async2", func=async_task_2, dependencies=["async1"])))
    workflow.add_task(Task(TaskConfig(task_id="async3", func=async_task_3, dependencies=["async2"])))
    
    result = await engine.run("async_demo")
    print_result(result)


# 主函数
def main():
    """运行所有示例"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           Agent-OS-Kernel 工作流引擎示例演示                   ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 运行各个示例
    demo_simple_linear_workflow()
    demo_parallel_workflow()
    demo_conditional_workflow()
    demo_error_handling()
    demo_data_pipeline()
    
    # 运行异步示例
    asyncio.run(demo_async_workflow())
    
    print("\n" + "=" * 60)
    print("  所有示例演示完成！")
    print("=" * 60)
    
    print("""
工作流引擎主要特性:
• DAG结构支持 - 复杂的任务依赖关系
• 拓扑排序 - 自动确定任务执行顺序
• 并行执行 - 提高执行效率
• 条件执行 - 根据运行时条件决定任务是否执行
• 错误处理 - 任务失败时自动重试
• 超时控制 - 防止任务无限期阻塞
• 状态跟踪 - 实时监控工作流执行状态
    """)


if __name__ == "__main__":
    main()
