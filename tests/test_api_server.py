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
    r = client.post("/api/v1/agents", headers=HEADERS,
                    json={"name": "ApiAgent", "task": "test", "priority": 40})
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
    r = client.post("/api/v1/context", headers=HEADERS,
                    json={"agent_id": aid, "content": "hello"})
    assert r.status_code == 200
    r = client.get(f"/api/v1/context/{aid}")
    assert r.status_code == 200
    assert "hello" in r.json()["context"]


def test_task_submit_and_query(client):
    r = client.post("/api/v1/agents", headers=HEADERS, json={"name": "A", "task": "t"})
    aid = r.json()["agent_id"]
    r = client.post("/api/v1/tasks", headers=HEADERS,
                    json={"agent_id": aid, "task": "do it"})
    assert r.status_code == 200
    tid = r.json()["task_id"]
    r = client.get(f"/api/v1/tasks/{tid}")
    assert r.status_code == 200
    assert r.json()["status"] == "pending"
    r = client.get("/api/v1/tasks/nope")
    assert r.status_code == 404


def test_task_submit_unknown_agent_404(client):
    r = client.post("/api/v1/tasks", headers=HEADERS,
                    json={"agent_id": "nope", "task": "x"})
    assert r.status_code == 404


def test_status_reports_version(client):
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    assert r.json()["version"] == "0.2.0"


def test_mutation_without_key_rejected(client):
    r = client.post("/api/v1/agents", json={"name": "X", "task": "t"})
    assert r.status_code == 401


def test_mutation_with_wrong_key_rejected(client):
    r = client.post("/api/v1/agents", headers={"X-API-Key": "wrong"},
                    json={"name": "X", "task": "t"})
    assert r.status_code == 401
