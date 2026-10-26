"""安全红线测试：P0-01 / P0-04 退出标准

审计（site/audit/report.md）退出标准：
- 读取 /etc/passwd、../、symlink escape、写 root 外路径、
  访问 169.254.169.254、shell metacharacter 等红队用例全部被拒绝
- 任何危险工具都不能在"无 sandbox"状态下运行
- 公开监听必须显式授权；匿名变更请求一律 401
"""

import pytest


class TestFileToolWorkspaceRoot:
    """文件工具必须限定在 workspace 根内"""

    def test_read_outside_workspace_denied(self, tmp_path):
        from agent_os_kernel.tools.builtin import FileReadTool

        tool = FileReadTool(allowed_roots=[str(tmp_path)])
        result = tool.execute("/etc/passwd")
        assert result["success"] is False
        assert result["metadata"].get("denied") is True

    def test_read_dotdot_escape_denied(self, tmp_path):
        from agent_os_kernel.tools.builtin import FileReadTool

        tool = FileReadTool(allowed_roots=[str(tmp_path / "workspace")])
        result = tool.execute(str(tmp_path / "workspace" / ".." / "secret.txt"))
        assert result["success"] is False
        assert result["metadata"].get("denied") is True

    def test_read_symlink_escape_denied(self, tmp_path):
        from agent_os_kernel.tools.builtin import FileReadTool

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        secret = tmp_path / "secret.txt"
        secret.write_text("TOPSECRET")
        link = workspace / "escape.txt"
        link.symlink_to(secret)
        tool = FileReadTool(allowed_roots=[str(workspace)])
        result = tool.execute(str(link))
        assert result["success"] is False
        assert result["metadata"].get("denied") is True

    def test_read_inside_workspace_allowed(self, tmp_path):
        from agent_os_kernel.tools.builtin import FileReadTool

        (tmp_path / "ok.txt").write_text("hello workspace")
        tool = FileReadTool(allowed_roots=[str(tmp_path)])
        result = tool.execute(str(tmp_path / "ok.txt"))
        assert result["success"] is True
        assert result["data"] == "hello workspace"

    def test_write_outside_workspace_denied(self, tmp_path):
        from agent_os_kernel.tools.builtin import FileWriteTool

        tool = FileWriteTool(allowed_roots=[str(tmp_path / "workspace")])
        result = tool.execute(str(tmp_path / "evil.txt"), "pwned")
        assert result["success"] is False
        assert result["metadata"].get("denied") is True
        assert not (tmp_path / "evil.txt").exists()

    def test_write_inside_workspace_allowed(self, tmp_path):
        from agent_os_kernel.tools.builtin import FileWriteTool

        tool = FileWriteTool(allowed_roots=[str(tmp_path)])
        result = tool.execute("sub/dir/ok.txt", "data")
        assert result["success"] is True
        assert (tmp_path / "sub" / "dir" / "ok.txt").read_text() == "data"


class TestPythonExecuteFailClosed:
    """PythonExecuteTool 无隔离时必须 fail closed"""

    def test_default_refuses_host_execution(self):
        from agent_os_kernel.tools.builtin import PythonExecuteTool

        tool = PythonExecuteTool()  # 未显式允许宿主执行
        result = tool.execute("print('should not run on host')")
        assert result["success"] is False
        assert result["metadata"].get("isolation_unavailable") is True
        assert "isolation_unavailable" in result["error"]

    def test_explicit_opt_in_executes(self, tmp_path):
        from agent_os_kernel.tools.builtin import PythonExecuteTool

        tool = PythonExecuteTool(allow_host_execution=True, allowed_roots=[str(tmp_path)])
        result = tool.execute("print('2+2 =', 2+2)")
        assert result["success"] is True
        assert "2+2 = 4" in result["data"]


class TestSandboxFailClosed:
    """SandboxManager 无 Docker 时不得伪装隔离"""

    def test_no_docker_means_no_isolation(self):
        from agent_os_kernel.core.security import SandboxManager

        mgr = SandboxManager()
        if mgr.docker_available:
            pytest.skip("docker available on this host")
        assert mgr.isolation_available() is False
        assert mgr.create_sandbox("agent-1") is None

    def test_execute_without_isolation_fails_closed(self):
        from agent_os_kernel.core.security import SandboxManager

        mgr = SandboxManager()
        if mgr.docker_available:
            pytest.skip("docker available on this host")
        # 手动放入一个"伪进程隔离"条目，模拟旧 fallback 数据
        mgr.containers["agent-1"] = {
            "type": "process",
            "workspace": "/tmp",
            "policy": __import__(
                "agent_os_kernel.core.security", fromlist=["SecurityPolicy"]
            ).SecurityPolicy(),
        }
        result = mgr.execute_in_sandbox("agent-1", "echo pwned")
        assert result["success"] is False
        assert result.get("isolation_unavailable") is True

    def test_explicit_host_fallback_uses_argv_no_shell(self, tmp_path):
        from agent_os_kernel.core.security import SandboxManager, SecurityPolicy

        mgr = SandboxManager()
        if mgr.docker_available:
            pytest.skip("docker available on this host")
        mgr.containers["agent-2"] = {
            "type": "process",
            "workspace": str(tmp_path),
            "policy": SecurityPolicy(),
        }
        result = mgr.execute_in_sandbox("agent-2", "echo safe", allow_host_fallback=True)
        assert result["success"] is True
        assert "safe" in result["stdout"]


class TestFileAccessPolicy:
    """validate_file_access 路径前缀必须按路径段匹配"""

    def test_prefix_sibling_not_matched(self):
        from agent_os_kernel.core.security import SandboxManager, SecurityPolicy

        mgr = SandboxManager()
        policy = SecurityPolicy(allowed_paths=["/tmp"], blocked_paths=["/etc"])
        mgr.containers["a"] = {"type": "process", "workspace": "/tmp", "policy": policy}
        # "/etcXXX" 不是 "/etc" 的子路径，但因 startswith 旧实现会被误判；
        # 语义上它应落在"未授权"区域（默认拒绝）
        assert mgr.validate_file_access("a", "/etcXXX/passwd") is False
        assert mgr.validate_file_access("a", "/tmp/ok.txt") is True
        assert mgr.validate_file_access("a", "/etc/passwd") is False


class TestWebFetchSSRF:
    """WebFetchTool 必须阻断私网/元数据端点"""

    def test_metadata_endpoint_blocked(self):
        from agent_os_kernel.tools.builtin import WebFetchTool

        tool = WebFetchTool()
        result = tool.execute("http://169.254.169.254/latest/meta-data/")
        assert result["success"] is False
        assert result["metadata"].get("blocked") is True

    def test_localhost_blocked(self):
        from agent_os_kernel.tools.builtin import WebFetchTool

        tool = WebFetchTool()
        result = tool.execute("http://127.0.0.1:8080/admin")
        assert result["success"] is False
        assert result["metadata"].get("blocked") is True

    def test_file_scheme_blocked(self):
        from agent_os_kernel.tools.builtin import WebFetchTool

        tool = WebFetchTool()
        result = tool.execute("file:///etc/passwd")
        assert result["success"] is False
        assert result["metadata"].get("blocked") is True
