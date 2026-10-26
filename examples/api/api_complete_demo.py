"""
Complete API Demo - 完整 API 演示

展示 REST API 的所有功能。

说明：原始版本依赖 aiohttp 并要求独立启动一个 HTTP 服务器。当前环境未安装
aiohttp，因此改用已安装的 httpx，通过 ASGITransport 在进程内直接驱动内核真实的
FastAPI 应用（AgentOSKernelAPI.create_app()），无需外部服务器即可完整体验所有
REST 端点（根路径/健康检查/Agent CRUD/任务/上下文/指标/Prometheus/清理）。
"""

import asyncio
import httpx
from typing import Any, Optional

from agent_os_kernel.api.server import AgentOSKernelAPI
from agent_os_kernel import AgentOSKernel


BASE_URL = "http://test"        # ASGI 进程内传输使用的占位 base_url
API_PREFIX = "/api/v1"
API_KEY = "demo-key"            # 变更型端点（POST/DELETE）需要 API Key


class APIClient:
    """API 客户端（httpx + ASGITransport，进程内直连内核 REST 应用）"""

    def __init__(self):
        self.api = AgentOSKernelAPI(api_key=API_KEY)
        self.app = self.api.create_app()
        # ASGITransport 不会触发 FastAPI 的 lifespan，这里手动完成内核初始化，
        # 与 lifespan 中的行为保持一致。
        self.api.kernel = AgentOSKernel()
        self.session: Optional[httpx.AsyncClient] = None

    async def connect(self):
        """连接（创建进程内 HTTP 客户端）"""
        self.session = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url=BASE_URL,
            headers={"X-API-Key": API_KEY},
            timeout=30.0,
        )
        print(f"✓ Connected to in-process Agent OS Kernel REST API")

    async def close(self):
        """关闭连接并关闭内核"""
        if self.session:
            await self.session.aclose()
        if self.api.kernel:
            self.api.kernel.shutdown()

    async def request(self, method: str, path: str, data: Any = None) -> Any:
        """发送请求（path 为完整路径，含 /api/v1 前缀）"""
        resp = await self.session.request(method, path, json=data)
        resp.raise_for_status()
        return resp.json()

    # ---- 根 / 健康 ----
    async def get_root(self) -> dict:
        return await self.request("GET", "/")

    async def get_health(self) -> dict:
        return await self.request("GET", "/health")

    async def get_ready(self) -> dict:
        # 当前内核没有 /ready 端点，用 /api/v1/status 体现就绪状态
        return await self.request("GET", f"{API_PREFIX}/status")

    # ---- Agent APIs ----
    async def list_agents(self) -> list:
        return await self.request("GET", f"{API_PREFIX}/agents")

    async def create_agent(self, name: str, task: str, priority: int = 50) -> dict:
        return await self.request("POST", f"{API_PREFIX}/agents",
                                  {"name": name, "task": task, "priority": priority})

    async def get_agent(self, agent_id: str) -> dict:
        return await self.request("GET", f"{API_PREFIX}/agents/{agent_id}")

    async def delete_agent(self, agent_id: str) -> dict:
        return await self.request("DELETE", f"{API_PREFIX}/agents/{agent_id}")

    # ---- Task APIs ----
    async def submit_task(self, agent_id: str, task: str) -> dict:
        return await self.request("POST", f"{API_PREFIX}/tasks",
                                  {"agent_id": agent_id, "task": task})

    async def get_task_result(self, task_id: str) -> dict:
        return await self.request("GET", f"{API_PREFIX}/tasks/{task_id}")

    # ---- Context APIs ----
    async def add_context(self, agent_id: str, content: str) -> dict:
        return await self.request("POST", f"{API_PREFIX}/context",
                                  {"agent_id": agent_id, "content": content})

    async def get_context(self, agent_id: str) -> dict:
        return await self.request("GET", f"{API_PREFIX}/context/{agent_id}")

    # ---- Metrics APIs ----
    async def get_metrics(self) -> dict:
        return await self.request("GET", f"{API_PREFIX}/metrics")

    async def get_prometheus_metrics(self) -> str:
        # Prometheus 文本经 FastAPI 以 JSON 字符串返回，这里解回纯文本
        resp = await self.session.get(f"{API_PREFIX}/metrics/prometheus")
        resp.raise_for_status()
        return resp.json()


async def demo_health_check(client: APIClient):
    """健康检查演示"""
    print("\n" + "=" * 60)
    print("Demo: Health Check")
    print("=" * 60)

    root = await client.get_root()
    print(f"✓ Root: {root['name']} v{root['version']}")

    health = await client.get_health()
    print(f"✓ Health: {health['status']}")

    ready = await client.get_ready()
    print(f"✓ Ready (status.running): {ready['running']}")

    metrics = await client.get_metrics()
    print(f"✓ Metrics: uptime={metrics['uptime_seconds']:.2f}s, "
          f"tracked={metrics['metrics']['total_metrics']}")


async def demo_agent_crud(client: APIClient):
    """Agent CRUD 演示"""
    print("\n" + "=" * 60)
    print("Demo: Agent CRUD")
    print("=" * 60)

    agent1 = await client.create_agent("Researcher", "Research AI trends", priority=30)
    print(f"✓ Created agent: {agent1['agent_id']}")

    agent2 = await client.create_agent("Writer", "Write technical docs", priority=50)
    print(f"✓ Created agent: {agent2['agent_id']}")

    agents = await client.list_agents()
    print(f"✓ Total agents: {len(agents)}")

    agent = await client.get_agent(agent1['agent_id'])
    print(f"✓ Get agent: {agent['name']} (state={agent['state']})")

    return [agent1['agent_id'], agent2['agent_id']]


async def demo_tasks(client: APIClient, agent_ids: list):
    """Task 演示"""
    print("\n" + "=" * 60)
    print("Demo: Task Submission")
    print("=" * 60)

    for agent_id in agent_ids:
        task = await client.submit_task(agent_id, "Introduce yourself")
        print(f"✓ Task submitted: {task['task_id']}")

        result = await client.get_task_result(task['task_id'])
        preview = result.get('result') or result.get('status', 'pending')
        print(f"  Status: {result.get('status')}  Result: {str(preview)[:50]}")


async def demo_context(client: APIClient, agent_id: str):
    """Context 演示"""
    print("\n" + "=" * 60)
    print("Demo: Context Management")
    print("=" * 60)

    r1 = await client.add_context(agent_id, "User prefers Python")
    print(f"✓ Context added: page {r1['page_id']}")

    r2 = await client.add_context(agent_id, "User is working on AI agents")
    print(f"✓ Another context added: page {r2['page_id']}")

    ctx = await client.get_context(agent_id)
    print(f"✓ Context length: {len(ctx['context'])} chars")


async def demo_metrics(client: APIClient):
    """Metrics 演示"""
    print("\n" + "=" * 60)
    print("Demo: Metrics")
    print("=" * 60)

    metrics = await client.get_metrics()
    print(f"✓ Uptime: {metrics['uptime_seconds']:.2f}s")
    print(f"✓ Tracked metrics: {metrics['metrics']['total_metrics']}")

    # Prometheus 格式
    prom = await client.get_prometheus_metrics()
    lines = [ln for ln in prom.strip().split('\n') if not ln.startswith('#')][:5]
    print(f"✓ Prometheus metrics (first 5):")
    for line in lines:
        print(f"  {line[:60]}")


async def demo_cleanup(client: APIClient, agent_ids: list):
    """清理演示"""
    print("\n" + "=" * 60)
    print("Demo: Cleanup")
    print("=" * 60)

    for agent_id in agent_ids:
        result = await client.delete_agent(agent_id)
        print(f"✓ Deleted: {agent_id} ({result['status']})")


async def main():
    """主函数"""
    print("=" * 60)
    print("🚀 Agent OS Kernel - Complete API Demo")
    print("=" * 60)

    client = APIClient()

    try:
        await client.connect()

        await demo_health_check(client)
        agent_ids = await demo_agent_crud(client)
        await demo_tasks(client, agent_ids)

        if agent_ids:
            await demo_context(client, agent_ids[0])

        await demo_metrics(client)
        await demo_cleanup(client, agent_ids)

        print("\n" + "=" * 60)
        print("✅ API Demo Complete!")
        print("=" * 60)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
