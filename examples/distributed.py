"""
Distributed Deployment Example

展示分布式部署配置
"""

import asyncio


async def demo_kubernetes():
    """Kubernetes 配置示例"""
    print("\n" + "=" * 60)
    print("Kubernetes Deployment")
    print("=" * 60)
    
    config = """# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-os-kernel
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-os-kernel
  template:
    metadata:
      labels:
        app: agent-os-kernel
    spec:
      containers:
      - name: kernel
        image: agent-os-kernel:latest
        ports:
        - containerPort: 8000
        env:
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
"""
    
    print(config)
    
    service = """# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: agent-os-kernel
spec:
  selector:
    app: agent-os-kernel
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
"""
    
    print(service)
    
    print("\n✓ Kubernetes 配置完成")


async def demo_docker_swarm():
    """Docker Swarm 配置"""
    print("\n" + "=" * 60)
    print("Docker Swarm Stack")
    print("=" * 60)
    
    config = """# docker-stack.yml
version: '3.8'
services:
  kernel:
    image: agent-os-kernel:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
    environment:
      - POSTGRES_URL=postgres://...
      - REDIS_URL=redis://...
    networks:
      - agent-network
    
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - agent-network
    
  redis:
    image: redis:7
    networks:
      - agent-network

networks:
  agent-network:
    driver: overlay
"""
    
    print(config)
    print("\n✓ Docker Swarm 配置完成")


async def demo_helm():
    """Helm Chart 配置"""
    print("\n" + "=" * 60)
    print("Helm Chart Values")
    print("=" * 60)
    
    values = """# helm/values.yaml
replicaCount: 3

image:
  repository: agent-os-kernel
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 80

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

postgresql:
  enabled: true
  postgresqlPassword: secret

redis:
  enabled: true
"""
    
    print(values)
    print("\n✓ Helm 配置完成")


async def demo_config_map():
    """配置管理"""
    print("\n" + "=" * 60)
    print("ConfigMap & Secrets")
    print("=" * 60)
    
    configmap = """# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-os-config
data:
  config.yaml: |
    kernel:
      max_agents: 100
      default_priority: 50
      timeout: 300
"""
    
    secret = """# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: agent-os-secret
type: Opaque
stringData:
  deepseek_api_key: "${DEEPSEEK_API_KEY}"
  kimi_api_key: "${KIMI_API_KEY}"
  postgres_url: "postgresql://..."
"""
    
    print(configmap)
    print(secret)
    print("\n✓ Config/Secret 配置完成")


async def demo_monitoring():
    """监控配置"""
    print("\n" + "=" * 60)
    print("Monitoring (Prometheus + Grafana)")
    print("=" * 60)
    
    prometheus = """# monitoring/prometheus.yaml
scrape_configs:
  - job_name: 'agent-os-kernel'
    metrics_path: /api/v1/metrics/prometheus
    static_configs:
      - targets: ['agent-os-kernel:8000']
"""
    
    print(prometheus)
    
    dashboard = """# monitoring/grafana-dashboard.json
{
  "dashboard": {
    "title": "Agent OS Kernel Metrics",
    "panels": [
      {
        "title": "Active Agents",
        "type": "graph",
        "targets": [
          {"expr": "agent_os_kernel_active_agents"}
        ]
      },
      {
        "title": "API Latency",
        "type": "graph",
        "targets": [
          {"expr": "histogram_quantile(0.95, rate(api_latency_seconds_bucket[5m]))"}
        ]
      }
    ]
  }
}
"""
    print(dashboard)
    
    print("\n✓ 监控配置完成")


async def main():
    print("=" * 60)
    print("🚀 Distributed Deployment Examples")
    print("=" * 60)
    
    await demo_kubernetes()
    await demo_docker_swarm()
    await demo_helm()
    await demo_config_map()
    await demo_monitoring()
    
    print("\n" + "=" * 60)
    print("✅ All deployment configurations ready!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
