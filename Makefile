.PHONY: help install test test-all lint format clean docs run doctor smoke

help:
	@echo "Agent-OS-Kernel 开发工具"
	@echo ""
	@echo "可用命令:"
	@echo "  make install    - 安装依赖（含 dev 工具）"
	@echo "  make test       - 运行测试套件"
	@echo "  make test-all   - 运行所有测试（含覆盖率）"
	@echo "  make lint       - 代码检查（ruff + mypy）"
	@echo "  make format     - 代码格式化（black）"
	@echo "  make clean      - 清理缓存"
	@echo "  make docs       - 文档链接检查"
	@echo "  make doctor     - 环境自检（黄金路径第一步）"
	@echo "  make smoke      - API 测试"
	@echo "  make run        - 运行确定性演示"

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -q

test-all:
	pytest tests/ -q --cov=agent_os_kernel --cov-report=term-missing

lint:
	ruff check agent_os_kernel/ tests/ scripts/
	mypy agent_os_kernel/ || true

format:
	black agent_os_kernel/ tests/ scripts/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist/

docs:
	python scripts/check_docs_links.py

doctor:
	python -m agent_os_kernel doctor

smoke:
	pytest tests/test_api_server.py -q

run:
	python -m agent_os_kernel demo --type checkpoint
