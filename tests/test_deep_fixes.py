"""深度检查发现的真 bug 回归测试（ruff F821/F841 审计产物）

覆盖三项修复：
1. benchmark: 失败调用不再伪装成延迟样本，error_count 单独计数
2. lock_manager: 阻塞 acquire 真正等待释放（原实现丢弃 wait_task 后
   重复建锁，互斥被破坏）
3. batch.clear_results: 按 completed_at 真正清理（原条件恒 False）
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from agent_os_kernel.core.benchmark import LatencyBenchmark
from agent_os_kernel.core.lock_manager import LockManager, LockType
from agent_os_kernel.core.optimization.batch import BatchProcessor, BatchResult


class TestBenchmarkErrorAccounting:
    def test_failures_counted_not_sampled(self):
        bench = LatencyBenchmark(warmup_iterations=0)

        def boom():
            raise ValueError("boom")

        result = bench.measure(boom, iterations=5, warmup=False)
        assert result.error_count == 5
        assert result.samples == []
        assert result.iterations == 0

    def test_mixed_success_and_failure(self):
        bench = LatencyBenchmark(warmup_iterations=0)
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] % 2 == 0:
                raise RuntimeError("half fail")

        result = bench.measure(flaky, iterations=6, warmup=False)
        assert result.error_count == 3
        assert len(result.samples) == 3
        assert result.iterations == 3


class TestLockManagerBlockingWait:
    @pytest.mark.asyncio
    async def test_blocking_acquire_waits_for_release(self):
        lm = LockManager(default_timeout=5.0)
        lock1 = await lm.acquire("res", "owner1")
        assert lock1 is not None

        acquired = []

        async def contender():
            lock = await lm.acquire(
                "res", "owner2", lock_type=LockType.MUTEX,
                blocking=True, timeout_seconds=5.0,
            )
            acquired.append(lock)

        task = asyncio.create_task(contender())
        await asyncio.sleep(0.1)

        # 竞争者必须仍在等待，且原持有者未被顶掉
        assert acquired == []
        assert lm._locks["res"].owner_id == "owner1"

        await lm.release("res", "owner1")
        await asyncio.wait_for(task, timeout=2.0)

        # 释放后竞争者才拿到锁
        assert len(acquired) == 1
        assert acquired[0] is not None
        assert lm._locks["res"].owner_id == "owner2"

    @pytest.mark.asyncio
    async def test_blocking_acquire_times_out(self):
        lm = LockManager(default_timeout=30.0)
        await lm.acquire("res", "owner1")

        lock = await lm.acquire(
            "res", "owner2", lock_type=LockType.MUTEX,
            blocking=True, timeout_seconds=0.2,
        )
        assert lock is None
        # 超时不破坏原锁
        assert lm._locks["res"].owner_id == "owner1"

    @pytest.mark.asyncio
    async def test_non_blocking_returns_none_while_held(self):
        lm = LockManager()
        await lm.acquire("res", "owner1")
        lock = await lm.acquire("res", "owner2", blocking=False)
        assert lock is None


class TestBatchClearResults:
    def test_old_results_removed_recent_kept(self):
        proc = BatchProcessor()
        proc._results["old"] = BatchResult(
            item_id="old", success=True,
            completed_at=datetime.now() - timedelta(hours=2),
        )
        proc._results["recent"] = BatchResult(
            item_id="recent", success=True, completed_at=datetime.now(),
        )

        proc.clear_results()

        assert "old" not in proc._results
        assert "recent" in proc._results

    def test_explicit_cutoff(self):
        proc = BatchProcessor()
        proc._results["a"] = BatchResult(
            item_id="a", success=True,
            completed_at=datetime(2020, 1, 1),
        )
        proc.clear_results(completed_before=datetime(2021, 1, 1))
        assert "a" not in proc._results


class TestCalculatorHardening:
    """calculator 从 eval+co_names 改为 AST 白名单后的逃逸/DoS 回归"""

    def setup_method(self):
        from agent_os_kernel.tools.builtin import CalculatorTool
        self.calc = CalculatorTool()

    def test_normal_expressions(self):
        cases = {
            "2 + 3 * 4": 14,
            "(2 + 3) * 4": 20,
            "sqrt(16) + abs(-2)": 6.0,
            "max(1, 5, 3)": 5,
            "7 % 3": 1,
            "2 ** 10": 1024,
            "-5 + 3": -2,
        }
        for expr, expected in cases.items():
            r = self.calc.execute(expression=expr)
            assert r["success"], f"{expr} failed: {r['error']}"
            assert r["data"] == expected, f"{expr} -> {r['data']} != {expected}"

    def test_sandbox_escapes_rejected(self):
        escapes = [
            "().__class__.__mro__[1].__subclasses__()",
            "(1).__class__.__bases__[0].__subclasses__()",
            "getattr(math, '__import__')('os')",
            "__import__('os').system('echo PWNED')",
            "open('/etc/passwd').read()",
            "[x for x in ().__class__.__mro__]",
            "'a' + 'b'",
            "lambda: 1",
            "1 if 2 else 3",
            "{}.__class__",
        ]
        for expr in escapes:
            r = self.calc.execute(expression=expr)
            assert not r["success"], f"ESCAPED: {expr} -> {r['data']}"

    def test_dos_rejected(self):
        for expr in ["9**9**9", "pow(9, 9**9)", "9**99999"]:
            r = self.calc.execute(expression=expr)
            assert not r["success"], f"DoS ACCEPTED: {expr}"

    def test_length_limit(self):
        r = self.calc.execute(expression="1+" * 400 + "1")
        assert not r["success"]
        assert "too long" in r["error"]
