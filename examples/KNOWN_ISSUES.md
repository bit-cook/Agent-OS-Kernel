# 已知问题：过期示例脚本（2026-10-26 实跑发现）

> 本文件由 `实际运行全部 examples/*.py` 生成。共 130 个示例，63 个通过、67 个失败。
> 失败根因：这些脚本写于早期 API 世代，之后内核 API 多次重构（TaskDefinition/
> CircuitConfig/RateLimiter/AgentRegistry 等签名变更、部分名字只在子模块存在、
> 部分同步方法改为异步），示例未同步更新。
> **库本身健康**：全量测试 666 passed / 0 failed；文档引用的 14 个示例全部修复可跑。

## 剩余失败清单（按根因聚类）

### other（6 个）

- `examples/advanced/worker_demo.py`
- `examples/api/api_demo.py`
- `examples/cache_system_demo.py`
- `examples/distributed_lock_demo.py`
- `examples/metrics_collector_demo.py`
- `examples/service_mesh_demo.py`

### CircuitConfig.__init__（3 个）

- `examples/basic/comprehensive_demo.py`
  - TypeError: CircuitConfig.__init__() got an unexpected keyword argument
- `examples/circuit_breaker_demo.py`
  - TypeError: CircuitConfig.__init__() got an unexpected keyword argument
- `examples/comprehensive_demo.py`
  - TypeError: CircuitConfig.__init__() got an unexpected keyword argument

### 'dict' object has no attribute 'role'（3 个）

- `examples/integration/local_llm_demo.py`
  - AttributeError: 'dict' object has no attribute 'role'
- `examples/integration/using_providers.py`
  - AttributeError: 'dict' object has no attribute 'role'
- `examples/quickstart/quickstart_demo.py`
  - AttributeError: 'dict' object has no attribute 'role'

### TaskDefinition.__init__（2 个）

- `examples/agent_definition_demo.py`
  - TypeError: TaskDefinition.__init__() got an unexpected keyword argumen
- `examples/basic/agent_definition_demo.py`
  - TypeError: TaskDefinition.__init__() got an unexpected keyword argumen

### AgentRegistry.register（2 个）

- `examples/agent_registry_demo.py`
  - TypeError: AgentRegistry.register() got an unexpected keyword argument
- `examples/basic/agent_registry_demo.py`
  - TypeError: AgentRegistry.register() got an unexpected keyword argument

### Message.__init__（2 个）

- `examples/async_queue_demo.py`
  - TypeError: Message.__init__() got an unexpected keyword argument 'cont
- `examples/basic/async_queue_demo.py`
  - TypeError: Message.__init__() got an unexpected keyword argument 'cont

### 'dict' object has no attribute 'batch_count'（2 个）

- `examples/basic/batch_processor_demo.py`
  - AttributeError: 'dict' object has no attribute 'batch_count'
- `examples/batch_processor_demo.py`
  - AttributeError: 'dict' object has no attribute 'batch_count'

### CacheSystem.set（2 个）

- `examples/basic/cache_demo.py`
  - TypeError: CacheSystem.set() got an unexpected keyword argument 'ttl'
- `examples/cache_demo.py`
  - TypeError: CacheSystem.set() got an unexpected keyword argument 'ttl'

### cannot import name 'CostBreakdown' from 'agent_o（2 个）

- `examples/basic/cost_tracker_demo.py`
  - ImportError: cannot import name 'CostBreakdown' from 'agent_os_kernel.
- `examples/cost_tracker_demo.py`
  - ImportError: cannot import name 'CostBreakdown' from 'agent_os_kernel.

### No module named 'agent_os_kernel.core.distribute（2 个）

- `examples/basic/distributed_demo.py`
  - ModuleNotFoundError: No module named 'agent_os_kernel.core.distributed
- `examples/distributed_demo.py`
  - ModuleNotFoundError: No module named 'agent_os_kernel.core.distributed

### 'LockManager' object has no attribute 'acquire_l（2 个）

- `examples/basic/lock_manager_demo.py`
  - AttributeError: 'LockManager' object has no attribute 'acquire_lock'
- `examples/lock_manager_demo.py`
  - AttributeError: 'LockManager' object has no attribute 'acquire_lock'

### 'MetricsCollector' object has no attribute 'reco（2 个）

- `examples/basic/metrics_demo.py`
  - AttributeError: 'MetricsCollector' object has no attribute 'record_cou
- `examples/metrics_demo.py`
  - AttributeError: 'MetricsCollector' object has no attribute 'record_cou

### EnumType.__call__（2 个）

- `examples/basic/pipeline_demo.py`
  - TypeError: EnumType.__call__() got an unexpected keyword argument 'nam
- `examples/pipeline_demo.py`
  - TypeError: EnumType.__call__() got an unexpected keyword argument 'nam

### RateLimiter.__init__（2 个）

- `examples/basic/rate_limiter_demo.py`
  - TypeError: RateLimiter.__init__() got an unexpected keyword argument '
- `examples/rate_limiter_demo.py`
  - TypeError: RateLimiter.__init__() got an unexpected keyword argument '

### type object 'PermissionLevel' has no attribute '（2 个）

- `examples/basic/security_demo.py`
  - AttributeError: type object 'PermissionLevel' has no attribute 'NONE'
- `examples/security_demo.py`
  - AttributeError: type object 'PermissionLevel' has no attribute 'NONE'

### cannot import name 'State' from 'agent_os_kernel（2 个）

- `examples/basic/state_machine_demo.py`
  - ImportError: cannot import name 'State' from 'agent_os_kernel.core.sta
- `examples/state_machine_demo.py`
  - ImportError: cannot import name 'State' from 'agent_os_kernel.core.sta

### type object 'StreamType' has no attribute 'REAL_（2 个）

- `examples/basic/stream_handler_demo.py`
  - AttributeError: type object 'StreamType' has no attribute 'REAL_TIME'
- `examples/stream_handler_demo.py`
  - AttributeError: type object 'StreamType' has no attribute 'REAL_TIME'

### cannot import name 'WorkflowNode' from 'agent_os（2 个）

- `examples/basic/workflow_engine_demo.py`
  - ImportError: cannot import name 'WorkflowNode' from 'agent_os_kernel.c
- `examples/workflow_engine_demo.py`
  - ImportError: cannot import name 'WorkflowNode' from 'agent_os_kernel.c

### 'NoneType' object has no attribute 'put'（2 个）

- `examples/integration/multi_agent_demo.py`
  - AttributeError: 'NoneType' object has no attribute 'put'
- `examples/quickstart/agent_complete_demo.py`
  - AttributeError: 'NoneType' object has no attribute 'put'

### AgentOSKernel.__init__（1 个）

- `examples/advanced/advanced_context_management.py`
  - TypeError: AgentOSKernel.__init__() got an unexpected keyword argument

### TaskManager.__init__（1 个）

- `examples/advanced/advanced_features_demo.py`
  - TypeError: TaskManager.__init__() got an unexpected keyword argument '

### BatchProcessor.__init__（1 个）

- `examples/advanced/batch_demo.py`
  - TypeError: BatchProcessor.__init__() got an unexpected keyword argumen

### can't subtract offset-naive and offset-aware dat（1 个）

- `examples/advanced/cache_demo.py`
  - TypeError: can't subtract offset-naive and offset-aware datetimes

### 'CircuitBreaker' object has no attribute 'get_st（1 个）

- `examples/advanced/circuit_breaker_demo.py`
  - AttributeError: 'CircuitBreaker' object has no attribute 'get_stats'

### cannot import name 'MetricsCollector' from 'agen（1 个）

- `examples/advanced/metrics_demo.py`
  - ImportError: cannot import name 'MetricsCollector' from 'agent_os_kern

### cannot import name 'CompressionConfig' from 'age（1 个）

- `examples/advanced/optimization_demo.py`
  - ImportError: cannot import name 'CompressionConfig' from 'agent_os_ker

### StateMachine.__init__（1 个）

- `examples/advanced/state_machine_demo.py`
  - TypeError: StateMachine.__init__() got an unexpected keyword argument 

### module 'asyncio' has no attribute 'coroutine'. D（1 个）

- `examples/agent_pool_enhanced_demo.py`
  - AttributeError: module 'asyncio' has no attribute 'coroutine'. Did you

### No module named 'aiohttp'（1 个）

- `examples/api/api_complete_demo.py`
  - ModuleNotFoundError: No module named 'aiohttp'

### EventBus.publish（1 个）

- `examples/api/event_bus_demo.py`
  - TypeError: EventBus.publish() got an unexpected keyword argument 'even

### 'AgentOSKernel' object has no attribute 'get_age（1 个）

- `examples/integration/agent_spawning.py`
  - AttributeError: 'AgentOSKernel' object has no attribute 'get_agent_sta

### cannot import name 'ClaudeIntegratedKernel' from（1 个）

- `examples/integration/claude_example.py`
  - ImportError: cannot import name 'ClaudeIntegratedKernel' from 'agent_o

### cannot import name 'AgentProcess' from 'agent_os（1 个）

- `examples/integration/claude_integration_example.py`
  - ImportError: cannot import name 'AgentProcess' from 'agent_os_kernel' 

### cannot import name 'init_mcp_registry' from 'age（1 个）

- `examples/integration/mcp_integration.py`
  - ImportError: cannot import name 'init_mcp_registry' from 'agent_os_ker

### 'Message'?（1 个）

- `examples/integration/multi_agent_collaboration.py`
  - NameError: name 'message' is not defined. Did you mean: 'Message'?

### cannot import name 'Hooks' from 'agent_os_kernel（1 个）

- `examples/integration/plugin_development.py`
  - ImportError: cannot import name 'Hooks' from 'agent_os_kernel.core.plu

### name 'create_plugin_manager' is not defined（1 个）

- `examples/integration/plugins.py`
  - NameError: name 'create_plugin_manager' is not defined

### 'StorageManager' object has no attribute 'get_au（1 个）

- `examples/quickstart/basic_usage.py`
  - AttributeError: 'StorageManager' object has no attribute 'get_audit_tr

### No module named 'agent_os_kernel.storage'（1 个）

- `examples/workflow/complete_workflow.py`
  - ModuleNotFoundError: No module named 'agent_os_kernel.storage'

### cannot import name 'AgentDefinition' from 'agent（1 个）

- `examples/workflow/production_workflow.py`
  - ImportError: cannot import name 'AgentDefinition' from 'agent_os_kerne

### TaskQueue.__init__（1 个）

- `examples/workflow/task_queue_demo.py`
  - TypeError: TaskQueue.__init__() got an unexpected keyword argument 'ma

### WorkflowEngine.create_workflow（1 个）

- `examples/workflow/workflow_demo.py`
  - TypeError: WorkflowEngine.create_workflow() got an unexpected keyword 
