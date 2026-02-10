# Agent-OS-Kernel Dockerfile

FROM python:3.11-slim

LABEL maintainer="bit-cook"
LABEL description="AI Agent Operating System Kernel"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY agent_os_kernel/ ./agent_os_kernel/
COPY agent_os_kernel.py .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

# Run the kernel
CMD ["python", "agent_os_kernel.py", "--host", "0.0.0.0", "--port", "8080"]
