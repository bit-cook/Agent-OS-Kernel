# API 参考文档

## 核心模块

### ContextManager (上下文管理器)
- 位置: `agent_os_kernel/core/context_manager.py`
- 功能: 虚拟内存式上下文管理
- 测试: `tests/test_context_manager.py` (17 tests)
- 示例: `examples/basic/context_manager_demo.py`

**主要方法:**
```python
ctx = ContextManager(max_context_tokens=100000)
page_id = ctx.allocate_page(agent_pid, content, importance)
context = ctx.get_agent_context(agent_pid)
ctx.release_agent_pages(agent_pid)
```

### StorageManager (存储管理器)
- 位置: `agent_os_kernel/core/storage.py`
- 功能: 五重角色存储
- 测试: `tests/test_storage_enhanced.py` (6 tests)
- 示例: `examples/basic/storage_demo.py`

**主要方法:**
```python
storage = StorageManager()
storage.save(key, data)
data = storage.retrieve(key)
exists = storage.exists(key)
storage.delete(key)
```

### EnhancedEventBus (事件总线)
- 位置: `agent_os_kernel/core/event_bus_enhanced.py`
- 功能: 发布/订阅事件系统
- 测试: `tests/test_event_bus.py` (8 tests)
- 示例: `examples/basic/event_bus_demo.py`

**主要方法:**
```python
bus = EnhancedEventBus()
bus.subscribe(event_type, handler)
await bus.publish_event(event_type, payload)
```

### Checkpointer (检查点)
- 位置: `agent_os_kernel/core/checkpointer.py`
- 功能: 状态保存/恢复
- 测试: `tests/test_checkpointer.py` (7 tests)
- 示例: `examples/basic/checkpointer_demo.py`

**主要方法:**
```python
cp = Checkpointer()
cp_id = await cp.create(name, state)
state = await cp.restore(cp_id)
checkpoints = await cp.list_checkpoints()
```

### CircuitBreaker (熔断器)
- 位置: `agent_os_kernel/core/circuit_breaker.py`
- 功能: 熔断保护
- 测试: `tests/test_circuit_breaker.py` (5 tests)
- 示例: `examples/basic/circuit_breaker_demo.py`

**主要方法:**
```python
cb = CircuitBreaker(name="service", failure_threshold=5)
state = cb.state  # CLOSED/OPEN/HALF_OPEN
cb.reset()
```

### AgentPool (Agent池)
- 位置: `agent_os_kernel/core/agent_pool.py`
- 功能: Agent对象池
- 测试: `tests/test_agent_pool.py` (3 tests)
- 示例: `examples/basic/agent_pool_demo.py`

**主要方法:**
```python
pool = AgentPool(max_size=5)
await pool.initialize()
await pool.shutdown()
```

### ConfigManager (配置管理)
- 位置: `agent_os_kernel/core/config_manager.py`
- 功能: 配置热加载
- 测试: `tests/test_config_manager.py` (3 tests)
- 示例: `examples/basic/config_manager_demo.py`

**主要方法:**
```python
cm = ConfigManager()
await cm.load("config_name", "/path/to/file")
value = await cm.get("name", "key")
await cm.set("name", "key", value)
```

### Observability (可观测性)
- 位置: `agent_os_kernel/core/observability.py`
- 功能: 事件追踪
- 测试: `tests/test_observability.py` (9 tests)
- 示例: `examples/basic/observability_demo.py`

**主要方法:**
```python
obs = Observability()
session = obs.start_session("session_name")
obs.record_event(event_type, agent_id, data)
session = obs.end_session()
```

### OptimizedScheduler (调度器)
- 位置: `agent_os_kernel/core/optimized_scheduler.py`
- 功能: 任务调度
- 测试: `tests/test_optimized_scheduler.py` (6 tests)
- 示例: `examples/basic/optimized_scheduler_demo.py`

**主要方法:**
```python
scheduler = OptimizedScheduler(max_concurrent=5)
task_id = await scheduler.schedule(name, func, priority)
result = await scheduler.get_result(task_id)
```

### MemoryFeedback (内存反馈)
- 位置: `agent_os_kernel/core/memory_feedback.py`
- 功能: 记忆反馈
- 测试: `tests/test_memory_enhancement.py` (9 tests)
- 示例: `examples/basic/memory_feedback_demo.py`

**主要方法:**
```python
feedback = MemoryFeedbackSystem()
await feedback.create_feedback(memory_id, type, content, reason)
pending = await feedback.get_pending_feedbacks()
```

### ToolMemory (工具内存)
- 位置: `agent_os_kernel/core/tool_memory.py`
- 功能: 工具调用追踪
- 测试: `tests/test_memory_enhancement.py` (3 tests)
- 示例: `examples/basic/tool_memory_demo.py`

**主要方法:**
```python
tool_mem = ToolMemory()
await tool_mem.record_call(tool_name, arguments, result, status)
stats = tool_mem.get_stats()
```

### PluginManager (插件管理)
- 位置: `agent_os_kernel/core/plugin_system.py`
- 功能: 插件生命周期
- 测试: `tests/test_plugin_manager.py` (7 tests)
- 示例: `examples/basic/plugin_system_demo.py`

**主要方法:**
```python
pm = PluginManager()
info = await pm.load_plugin(plugin_class)
await pm.enable_plugin(name)
await pm.disable_plugin(name)
```

### LLM Provider
- 位置: `agent_os_kernel/llm/provider.py`
- 功能: 多模型抽象
- 测试: `tests/test_llm_provider.py` (9 tests)
- 示例: `examples/basic/llm_provider_demo.py`

**主要方法:**
```python
config = LLMConfig(provider=Type.OPENAI, model="gpt-4")
result = await provider.chat(messages)
embeddings = await provider.embeddings(texts)
tokens = await provider.count_tokens(text)
```

## 枚举类型

### EventType (事件类型)
```python
from agent_os_kernel.core.event_bus_enhanced import EventType

EventType.TASK_STARTED
EventType.TASK_COMPLETED
EventType.AGENT_CREATED
EventType.SYSTEM_ERROR
# ... etc
```

### EventPriority (事件优先级)
```python
from agent_os_kernel.core.event_bus_enhanced import EventPriority

EventPriority.LOW
EventPriority.NORMAL
EventPriority.HIGH
EventPriority.CRITICAL
```

### Priority (调度优先级)
```python
from agent_os_kernel.core.optimized_scheduler import Priority

Priority.CRITICAL
Priority.HIGH
Priority.NORMAL
Priority.LOW
Priority.BACKGROUND
```

### ProviderType (Provider类型)
```python
from agent_os_kernel.llm.provider import ProviderType

ProviderType.OPENAI
ProviderType.ANTHROPIC
ProviderType.DEEPSEEK
ProviderType.OLLAMA
ProviderType.VLLM
# ... etc
```

## 异常类型

```python
from agent_os_kernel.core.exceptions import (
    AgentOSKernelError,
    AgentError,
    ContextOverflowError,
    ValidationError,
    SecurityError,
    ConfigurationError
)
```
