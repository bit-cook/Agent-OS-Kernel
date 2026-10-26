"""
API Server Demo
展示 REST API 的使用方式。

说明：原始版本依赖一个独立启动的 uvicorn 服务器（requests 访问 localhost:8000）。
为避免依赖外部进程，这里改用 FastAPI 进程内 TestClient 直连内核真实的 REST 应用，
完整体验根路径、健康检查、Agent CRUD、上下文、指标、状态与 Prometheus 等端点。
"""

import json

from fastapi.testclient import TestClient

from agent_os_kernel.api.server import AgentOSKernelAPI
from agent_os_kernel import AgentOSKernel


API_KEY = "demo-key"   # 变更型端点（POST/DELETE）需要 API Key


def show(resp):
    """打印响应（JSON 美化或文本）。"""
    ct = resp.headers.get("content-type", "")
    if "application/json" in ct:
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    else:
        print(resp.text[:500] + "...")


def demo_root(client):
    """根路径"""
    print("\n=== Root ===")
    show(client.get("/"))


def demo_health(client):
    """健康检查"""
    print("\n=== Health Check ===")
    show(client.get("/health"))


def demo_create_agent(client):
    """创建 Agent"""
    print("\n=== Create Agent ===")

    data = {
        "name": "API-Demo-Agent",
        "task": "通过 API 创建的 Agent",
        "priority": 50
    }

    resp = client.post("/api/v1/agents", json=data)
    show(resp)

    return resp.json()["agent_id"]


def demo_list_agents(client):
    """列出 Agent"""
    print("\n=== List Agents ===")
    show(client.get("/api/v1/agents"))


def demo_get_agent(client, agent_id):
    """获取 Agent"""
    print("\n=== Get Agent ===")
    show(client.get(f"/api/v1/agents/{agent_id}"))


def demo_add_context(client, agent_id):
    """添加上下文"""
    print("\n=== Add Context ===")

    data = {
        "agent_id": agent_id,
        "content": "这是通过 API 添加的上下文内容"
    }

    show(client.post("/api/v1/context", json=data))


def demo_metrics(client):
    """获取指标"""
    print("\n=== Metrics ===")
    show(client.get("/api/v1/metrics"))


def demo_status(client):
    """系统状态"""
    print("\n=== Status ===")
    show(client.get("/api/v1/status"))


def demo_prometheus_metrics(client):
    """Prometheus 指标"""
    print("\n=== Prometheus Metrics ===")
    resp = client.get("/api/v1/metrics/prometheus")
    # FastAPI 将字符串以 JSON 返回，解回纯文本
    text = resp.json()
    print(text[:500] + "...")


def main():
    print("=" * 60)
    print("🚀 Agent OS Kernel API Demo")
    print("=" * 60)

    # 进程内构建 REST 客户端（含认证头）；TestClient 未作为上下文管理器使用时
    # 不会触发 lifespan，因此手动完成内核初始化，与 lifespan 行为一致。
    api = AgentOSKernelAPI(api_key=API_KEY)
    app = api.create_app()
    api.kernel = AgentOSKernel()
    client = TestClient(app, headers={"X-API-Key": API_KEY})

    try:
        demo_root(client)
        demo_health(client)
        agent_id = demo_create_agent(client)
        demo_list_agents(client)
        demo_get_agent(client, agent_id)
        demo_add_context(client, agent_id)
        demo_metrics(client)
        demo_status(client)
        demo_prometheus_metrics(client)

        print("\n" + "=" * 60)
        print("✅ API Demo Complete!")
        print("=" * 60)
    finally:
        if api.kernel:
            api.kernel.shutdown()


if __name__ == "__main__":
    main()
