"""
API Server Demo

展示 REST API 的使用方式
"""

import requests
import json


BASE_URL = "http://localhost:8000"


def demo_root():
    """根路径"""
    print("\n=== Root ===")
    resp = requests.get(f"{BASE_URL}/")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))


def demo_health():
    """健康检查"""
    print("\n=== Health Check ===")
    resp = requests.get(f"{BASE_URL}/health")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))


def demo_create_agent():
    """创建 Agent"""
    print("\n=== Create Agent ===")
    
    data = {
        "name": "API-Demo-Agent",
        "task": "通过 API 创建的 Agent",
        "priority": 50
    }
    
    resp = requests.post(f"{BASE_URL}/api/v1/agents", json=data)
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    
    return resp.json()["agent_id"]


def demo_list_agents():
    """列出 Agent"""
    print("\n=== List Agents ===")
    resp = requests.get(f"{BASE_URL}/api/v1/agents")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))


def demo_get_agent(agent_id):
    """获取 Agent"""
    print("\n=== Get Agent ===")
    resp = requests.get(f"{BASE_URL}/api/v1/agents/{agent_id}")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))


def demo_metrics():
    """获取指标"""
    print("\n=== Metrics ===")
    resp = requests.get(f"{BASE_URL}/api/v1/metrics")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))


def demo_status():
    """系统状态"""
    print("\n=== Status ===")
    resp = requests.get(f"{BASE_URL}/api/v1/status")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))


def demo_add_context(agent_id):
    """添加上下文"""
    print("\n=== Add Context ===")
    
    data = {
        "agent_id": agent_id,
        "content": "这是通过 API 添加的上下文内容"
    }
    
    resp = requests.post(f"{BASE_URL}/api/v1/context", json=data)
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))


def demo_prometheus_metrics():
    """Prometheus 指标"""
    print("\n=== Prometheus Metrics ===")
    resp = requests.get(f"{BASE_URL}/api/v1/metrics/prometheus")
    print(resp.text[:500] + "...")


def main():
    print("=" * 60)
    print("🚀 Agent OS Kernel API Demo")
    print("=" * 60)
    
    # 启动服务器后运行此 demo
    # uvicorn agent_os_kernel.api.server:AgentOSKernelAPI --host 0.0.0.0 --port 8000
    
    demo_root()
    demo_health()
    demo_create_agent()
    demo_list_agents()
    demo_get_agent("agent-1")
    demo_add_context("agent-1")
    demo_metrics()
    demo_status()
    demo_prometheus_metrics()
    
    print("\n" + "=" * 60)
    print("✅ API Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
