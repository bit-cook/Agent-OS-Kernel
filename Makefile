.PHONY: help install test lint format clean docs run

help:
	@echo "Agent-OS-Kernel 开发工具"
	@echo ""
	@echo "可用命令:"
	@echo "  make install    - 安装依赖"
	@echo "  make test       - 运行测试"
	@echo "  make test-all   - 运行所有测试"
	@echo "  make lint       - 代码检查"
	@echo "  make format     - 代码格式化"
	@echo "  make clean      - 清理缓存"
	@echo "  make docs       - 生成文档"
	@echo "  make run        - 运行示例"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	pytest tests/test_core.py tests/test_types.py -v

test-all:
	pytest tests/ -v --tb=short

lint:
	ruff check agent_os_kernel/
	mypy agent_os_kernel/

format:
	black agent_os_kernel/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

docs:
	python -m pydoc -w agent_os_kernel

run:
	python examples/comprehensive_system_demo.py
