# Agent-OS-Kernel Makefile

.PHONY: all install dev test lint format clean docker deploy docs

# 安装依赖
install:
	pip install -r requirements.txt

# 开发依赖
dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# 运行测试
test:
	pytest tests/ -v --cov=agent_os_kernel --cov-report=term-missing

# 快速测试
test-quick:
	pytest tests/ -v --tb=short

# 类型检查
lint:
	black --check agent_os_kernel/ tests/
	flake8 agent_os_kernel/ tests/ --max-line-length=100
	mypy agent_os_kernel/ --ignore-missing-imports

# 代码格式化
format:
	black agent_os_kernel/ tests/

# 清理
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf build/ dist/ *.egg-info/

# Docker 构建
docker:
	docker build -t agent-os-kernel:latest .

# Docker 运行
docker-run:
	docker run -p 8080:8080 agent-os-kernel:latest

# 生成文档
docs:
	@echo "Docs generation not configured. Install sphinx and run 'make html' in docs/"

# 运行示例
run-example:
	@echo "Running basic_usage.py..."
	@python examples/basic_usage.py

# 运行基准测试
benchmark:
	@echo "Running benchmark.py..."
	@python examples/benchmark.py

# 检查依赖
check-deps:
	@echo "Checking dependencies..."
	@pip list | grep -E "agent-os-kernel|psutil|pyyaml|requests"

# 创建虚拟环境
venv:
	python -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip

# 帮助
help:
	@echo "Agent-OS-Kernel Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  install     - Install dependencies"
	@echo "  dev         - Install dev dependencies"
	@echo "  test        - Run full test suite"
	@echo "  test-quick  - Run quick tests"
	@echo "  lint        - Run code quality checks"
	@echo "  format      - Format code with black"
	@echo "  clean       - Clean build artifacts"
	@echo "  docker      - Build Docker image"
	@echo "  docker-run  - Run Docker container"
	@echo "  benchmark   - Run benchmarks"
	@echo "  help        - Show this help"
