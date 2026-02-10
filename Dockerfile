# Agent OS Kernel - Optimized Docker Image

# Build stage
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Production stage
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application
COPY agent_os_kernel/ ./agent_os_kernel/
COPY pyproject.toml README.md ./

# Install package
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd --create-home --shell /bin/bash agent && \
    chown -R agent:agent /app
USER agent

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import agent_os_kernel" || exit 1

# Default command
CMD ["python", "-m", "agent_os_kernel", "--demo", "basic"]
