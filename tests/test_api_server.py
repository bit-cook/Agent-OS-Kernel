"""API contract tests: golden-path endpoints + auth against the real app.

对应审计 P0-03（API 调用的方法必须存在且行为真实）与
P0-04（默认 loopback、变更端点认证、无虚假成功）。
"""

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from agent_os_kernel.api.server import AgentOSKernelAPI


@pytest.fixture()
def client():
    api = AgentOSKernelAPI(api_key="test-key-123")
    app = api.create_app()
    with TestClient(app) as c:
        yield c


HEADERS = {"X-API-Key": "test-key-123"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["version"] == "0.2.0"


def test_create_and_get_agent(client):
    r = client.post(
        "/api/v1/agents", headers=HEADERS, json={"name": "ApiAgent", "task": "test", "priority": 40}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "ready"
    aid = body["agent_id"]

    r = client.get(f"/api/v1/agents/{aid}")
    assert r.status_code == 200
    assert r.json()["name"] == "ApiAgent"

    r = client.get("/api/v1/agents/nonexistent")
    assert r.status_code == 404


def test_list_agents(client):
    client.post("/api/v1/agents", headers=HEADERS, json={"name": "A", "task": "t"})
    r = client.get("/api/v1/agents")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_delete_agent_is_real(client):
    r = client.post("/api/v1/agents", headers=HEADERS, json={"name": "A", "task": "t"})
    aid = r.json()["agent_id"]
    r = client.delete(f"/api/v1/agents/{aid}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["status"] == "deleted"
    # 删除是真实的：再查应 404
    r = client.get(f"/api/v1/agents/{aid}")
    assert r.status_code == 404


def test_context_shares_kernel_state(client):
    r = client.post("/api/v1/agents", headers=HEADERS, json={"name": "A", "task": "t"})
    aid = r.json()["agent_id"]
    r = client.post("/api/v1/context", headers=HEADERS, json={"agent_id": aid, "content": "hello"})
    assert r.status_code == 200
    r = client.get(f"/api/v1/context/{aid}")
    assert r.status_code == 200
    assert "hello" in r.json()["context"]


def test_task_submit_and_query(client):
    r = client.post("/api/v1/agents", headers=HEADERS, json={"name": "A", "task": "t"})
    aid = r.json()["agent_id"]
    r = client.post("/api/v1/tasks", headers=HEADERS, json={"agent_id": aid, "task": "do it"})
    assert r.status_code == 200
    tid = r.json()["task_id"]
    r = client.get(f"/api/v1/tasks/{tid}")
    assert r.status_code == 200
    assert r.json()["status"] == "pending"
    r = client.get("/api/v1/tasks/nope")
    assert r.status_code == 404


def test_task_submit_unknown_agent_404(client):
    r = client.post("/api/v1/tasks", headers=HEADERS, json={"agent_id": "nope", "task": "x"})
    assert r.status_code == 404


def test_status_reports_version(client):
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    assert r.json()["version"] == "0.2.0"


def test_mutation_without_key_rejected(client):
    r = client.post("/api/v1/agents", json={"name": "X", "task": "t"})
    assert r.status_code == 401


def test_mutation_with_wrong_key_rejected(client):
    r = client.post(
        "/api/v1/agents", headers={"X-API-Key": "wrong"}, json={"name": "X", "task": "t"}
    )
    assert r.status_code == 401


def test_ui_dashboard_served(client):
    """控制面板页面必须真实提供（此前 static 目录是孤儿文件）"""
    r = client.get("/ui")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    # 自包含：不得依赖外部 CDN
    assert "cdn.tailwindcss.com" not in body
    assert "unpkg.com" not in body
    # 必须调用真实存在的端点（BASE='/api/v1' 动态拼接）
    assert "/api/v1" in body
    assert "'/agents'" in body
    assert "'/checkpoints'" in body
    assert "'/tools'" in body
    assert "'/audit" in body


def test_tools_endpoint_real(client):
    """工具列表必须是真实注册表的 schema"""
    r = client.get("/api/v1/tools")
    assert r.status_code == 200
    tools = r.json()["tools"]
    assert len(tools) >= 5
    names = {t.get("name") for t in tools}
    assert {"calculator", "read_file", "write_file", "execute_python"} <= names


def test_checkpoint_create_and_restore_real(client):
    """检查点创建/恢复必须是真实内核操作（非占位）"""
    r = client.post("/api/v1/agents", headers=HEADERS, json={"name": "CP", "task": "t"})
    aid = r.json()["agent_id"]

    # 创建检查点
    r = client.post(f"/api/v1/agents/{aid}/checkpoints", headers=HEADERS)
    assert r.status_code == 200
    cid = r.json()["checkpoint_id"]
    assert cid

    # 检查点出现在列表中，且带上下文页面
    r = client.get("/api/v1/checkpoints")
    assert r.status_code == 200
    cps = r.json()["checkpoints"]
    assert any(c["checkpoint_id"] == cid for c in cps)
    cp = next(c for c in cps if c["checkpoint_id"] == cid)
    assert len(cp.get("context_pages", [])) >= 3

    # 恢复：产生新 PID
    r = client.post(f"/api/v1/checkpoints/{cid}/restore", headers=HEADERS)
    assert r.status_code == 200
    new_pid = r.json()["new_agent_id"]
    assert new_pid and new_pid != aid
    assert client.get(f"/api/v1/agents/{new_pid}").status_code == 200


def test_checkpoint_unknown_agent_404(client):
    r = client.post("/api/v1/agents/nonexistent/checkpoints", headers=HEADERS)
    assert r.status_code == 404


def test_restore_unknown_checkpoint_404(client):
    r = client.post("/api/v1/checkpoints/nonexistent/restore", headers=HEADERS)
    assert r.status_code == 404


def test_audit_endpoint_real(client):
    """审计日志端点返回真实记录"""
    r = client.get("/api/v1/audit?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json()["logs"], list)


class TestAgentStepEndpoint:
    """POST /api/v1/agents/{id}/step：API 层真实驱动 LLM step（审查 P1-06）"""

    def test_step_drives_real_llm_call(self, client):
        create = client.post(
            "/api/v1/agents",
            headers=HEADERS,
            json={
                "name": "StepAgent",
                "task": "验证 step 端点",
                "priority": 30,
            },
        )
        assert create.status_code == 200
        agent_id = create.json()["agent_id"]

        resp = client.post(f"/api/v1/agents/{agent_id}/step")
        assert resp.status_code == 200
        body = resp.json()
        assert body["step"] == 1
        assert body["success"] is True
        assert body["reasoning"]  # 真实 provider 响应内容

        # 审计记录标注 provider 模式
        audit = client.get("/api/v1/audit")
        assert audit.status_code == 200
        entries = audit.json()
        logs = (
            entries
            if isinstance(entries, list)
            else entries.get("logs", entries.get("entries", []))
        )
        llm_logs = [l for l in logs if "llm" in str(l.get("resource", ""))]
        assert llm_logs, "audit should record the LLM step"
        assert llm_logs[-1]["details"]["mode"] == "provider"

    def test_step_unknown_agent_404(self, client):
        resp = client.post("/api/v1/agents/nonexistent/step")
        assert resp.status_code == 404
