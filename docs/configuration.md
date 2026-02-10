# 配置管理

## 概述

Agent OS Kernel 提供强大的配置管理系统，支持多环境配置、动态更新、配置热加载。

## 快速开始

### 基本配置

```python
from agent_os_kernel.core.config_manager import ConfigManager

manager = ConfigManager(config_dir="config")
await manager.initialize()

# 获取配置
app_name = await manager.get("app", "name")
db_host = await manager.get("database", "host")
```

### YAML 配置示例

```yaml
# config/app.yaml
app:
  name: "AgentOSKernel"
  version: "1.0.0"
  debug: true

database:
  host: "localhost"
  port: 5432
  pool_size: 10

llm:
  default_model: "gpt-4o"
  timeout: 60
```

## 核心功能

### 1. 多环境配置

支持环境变量覆盖：

```python
# 使用环境变量
export AGENT_OS_DEBUG=true
export DATABASE_HOST=prod-db.example.com

# 自动读取环境变量
await manager.load("app")
debug = await manager.get("app", "app/debug")  # true
```

### 2. 配置热加载

启用热加载：

```python
manager = ConfigManager(
    config_dir="config",
    enable_hot_reload=True,
    hot_reload_interval=30  # 每30秒检查
)
await manager.initialize()
```

### 3. 配置监听

监听配置变更：

```python
async def on_config_change(config):
    print(f"Config {config.name} updated")

manager.watch("app", on_config_change)
```

## API 参考

### ConfigManager

| 方法 | 说明 |
|------|------|
| `load(name, file_path)` | 加载配置 |
| `get(name, key, default)` | 获取配置 |
| `set(name, key, value)` | 设置配置 |
| `delete(name, key)` | 删除配置 |
| `list_configs()` | 列出所有配置 |
| `watch(name, callback)` | 监听变更 |

## 最佳实践

1. **配置文件分离**
   - 按功能分文件
   - 环境特定配置

2. **敏感信息**
   - 使用环境变量
   - 不要提交到版本控制

3. **配置验证**
   - 使用默认值
   - 添加类型检查
