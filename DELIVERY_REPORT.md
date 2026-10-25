# Agent-OS-Kernel 深度完善交付报告

仓库: https://github.com/bit-cook/Agent-OS-Kernel
本地提交: 75d04c1（工作树 /root/.hermes/cache/scratch/Agent-OS-Kernel）
测试: 649 passed / 0 failed（基线: 套件因死锁永久挂起）

## P0 全部完成（按仓库自带审查报告 site/audit/report.md 退出标准）

1. 黄金路径 (P0-03)
- 顶层导出修复: from agent_os_kernel import AgentOSKernel 从 ImportError 到可用
- CLI 重写: doctor 环境自检 4 项全过; create/list/status/demo 真实执行
  (demo 跑通 spawn→run→checkpoint→restore 闭环)
- API 重写: 冒烟 15/15 全绿 (创建/查询/删除/上下文共享/任务/认证 401)
- 删除 525 行重复 CLI; __main__/入口统一; 修掉主循环每步崩溃的
  log_action 隐藏 bug

2. Checkpoint 契约 (P0-02)
- scheduler/kernel/storage 三层统一单一 dict 契约
- 实测: 检查点含 3 页上下文, 恢复后 3 页回到新进程
- FILE 后端 list_keys 哈希不可反推的 bug 修复

3. 安全 (P0-01, 红队测试 15 项全过)
- 文件工具 workspace 根约束: /etc/passwd、../、symlink escape 全部拒绝
- PythonExecuteTool 默认 fail-closed (isolation_unavailable)
- SandboxManager 无 Docker 时不再伪装隔离; shell=True 全部移除
- WebFetchTool SSRF 防护: 169.254.169.254/私网/环回/file scheme 阻断

4. API 暴露面 (P0-04)
- 默认 127.0.0.1; 变更端点 API Key 认证 (实测无 key/错 key 均 401)

## 测试与构建
- 修复套件跑 14 小时的死锁根因 (persist_lock/CircuitBreaker: Lock→RLock)
- 修复 30+ 个存量失败, 涉及 12 个模块 (message_queue/task_scheduler/
  distributed_lock/countdown_timer/plugin_system/state_machine/
  workflow_engine/connection_pool/metrics_collector/service_mesh 等)
- 4 处测试间契约矛盾按"更显式契约为准"修正 (已在提交信息记录)
- pyproject extras 统一 (CI 不再 exit 127); CI 重写 (ruff+black+mypy ratchet+
  wheel 干净目录冒烟+文档链接检查); 版本统一 0.2.0-alpha; 48 个文档链接全过
- 新增测试: test_security_hardening.py (15 项红队) + test_api_server.py (11 项契约)

## 卡点
推送需要 GitHub 写权限 token (本机无 gh CLI/无凭据)。提供 token 后
我立即推送并更新远程; 或当前本地提交可直接作为补丁使用。
