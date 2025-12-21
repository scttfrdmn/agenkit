# Deploying Agenkit Agents to Production

Complete guide for deploying AI agents with Docker, Kubernetes, CI/CD, and monitoring.

## What You'll Learn

1. **Docker** - Containerize agents for portability
2. **Docker Compose** - Multi-service orchestration
3. **Kubernetes** - Production-grade deployment
4. **CI/CD** - Automated testing and deployment
5. **Monitoring** - Observability with Prometheus & Grafana
6. **Best Practices** - Security, scaling, and reliability

## Prerequisites

- Completed Tutorials 01-03
- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- (Optional) Kubernetes cluster access
- (Optional) GitHub account for CI/CD examples

## Quick Start

```bash
# Clone this directory
cd tutorials/04-deployment

# Build and run with Docker
docker build -t my-agent .
docker run -p 8000:8000 my-agent

# Or use Docker Compose
docker-compose up

# For Kubernetes
kubectl apply -f k8s/
```

---

## 1. Docker: Containerizing Agents

### Why Docker?

- **Portability**: Run anywhere Docker runs
- **Consistency**: Same environment dev → prod
- **Isolation**: Dependencies don't conflict
- **Efficiency**: Lightweight compared to VMs

### Basic Dockerfile

See [`Dockerfile`](./Dockerfile) for a complete example. Key sections:

```dockerfile
# Multi-stage build for smaller images
FROM python:3.11-slim as builder

# Install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local

# Copy application
COPY . /app
WORKDIR /app

# Run agent
CMD ["python", "-m", "agenkit.server"]
```

### Building and Running

```bash
# Build image
docker build -t my-agent:v1 .

# Run locally
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  my-agent:v1

# Test agent
curl http://localhost:8000/health
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Hello!"}'
```

### Best Practices

1. **Multi-stage builds** - Reduce image size
2. **Layer caching** - Put dependencies before app code
3. **Non-root user** - Security best practice
4. **Health checks** - Docker can restart unhealthy containers
5. **.dockerignore** - Don't copy unnecessary files
6. **Secrets management** - Use environment variables or secrets

---

## 2. Docker Compose: Multi-Service Orchestration

### Why Docker Compose?

- **Multiple services**: Agent + database + cache
- **Easy configuration**: YAML-based setup
- **Development parity**: Local env matches prod
- **Networking**: Automatic service discovery

### Example Setup

See [`docker-compose.yml`](./docker-compose.yml) for complete configuration.

```yaml
services:
  agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=secret
    volumes:
      - postgres-data:/var/lib/postgresql/data

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

### Running Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f agent

# Stop all services
docker-compose down

# With volume cleanup
docker-compose down -v
```

### Example Agent with Dependencies

```python
# app.py - Agent with Redis caching
from agenkit import Agent, Message
from agenkit.middleware import CachingMiddleware
from agenkit.transports import HTTPServer
import redis
import os

# Your agent
class MyAgent(Agent):
    def name(self) -> str:
        return "my-agent"

    async def process(self, message: Message) -> Message:
        # Your logic here
        return Message(role="assistant", content="Response")

# Add caching
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
agent = CachingMiddleware(MyAgent(), redis_client=redis_client)

# Serve over HTTP
server = HTTPServer(agent, host="0.0.0.0", port=8000)
server.start()
```

---

## 3. Kubernetes: Production Deployment

### Why Kubernetes?

- **Scaling**: Automatically scale based on load
- **Self-healing**: Replace failed containers
- **Rolling updates**: Zero-downtime deployments
- **Load balancing**: Distribute traffic
- **Resource management**: CPU/memory limits

### Architecture

```
┌─────────────────────────────────────────┐
│            Load Balancer                │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│          Service (ClusterIP)            │
└───┬────────────────┬──────────────────┬─┘
    │                │                  │
┌───▼────┐      ┌────▼───┐      ┌──────▼──┐
│ Pod 1  │      │ Pod 2  │      │  Pod 3  │
│ Agent  │      │ Agent  │      │  Agent  │
│ Redis  │      │ Redis  │      │  Redis  │
└────────┘      └────────┘      └─────────┘
```

### Kubernetes Manifests

See [`k8s/`](./k8s/) directory for complete examples:

- [`deployment.yaml`](./k8s/deployment.yaml) - Agent deployment
- [`service.yaml`](./k8s/service.yaml) - Service definition
- [`ingress.yaml`](./k8s/ingress.yaml) - External access
- [`configmap.yaml`](./k8s/configmap.yaml) - Configuration
- [`secret.yaml`](./k8s/secret.yaml) - Sensitive data
- [`hpa.yaml`](./k8s/hpa.yaml) - Horizontal Pod Autoscaler

#### Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenkit-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agenkit-agent
  template:
    metadata:
      labels:
        app: agenkit-agent
    spec:
      containers:
      - name: agent
        image: my-agent:v1
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Deploying to Kubernetes

```bash
# Create namespace
kubectl create namespace agenkit

# Create secrets
kubectl create secret generic agent-secrets \
  --from-literal=openai-api-key=$OPENAI_API_KEY \
  -n agenkit

# Apply manifests
kubectl apply -f k8s/ -n agenkit

# Check status
kubectl get pods -n agenkit
kubectl get services -n agenkit

# View logs
kubectl logs -f deployment/agenkit-agent -n agenkit

# Scale deployment
kubectl scale deployment agenkit-agent --replicas=5 -n agenkit

# Update deployment (rolling update)
kubectl set image deployment/agenkit-agent agent=my-agent:v2 -n agenkit

# Check rollout status
kubectl rollout status deployment/agenkit-agent -n agenkit

# Rollback if needed
kubectl rollout undo deployment/agenkit-agent -n agenkit
```

### Autoscaling

Enable Horizontal Pod Autoscaler (HPA):

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agenkit-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agenkit-agent
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 4. CI/CD: Automated Deployment

### Why CI/CD?

- **Automation**: Deploy on every commit
- **Testing**: Run tests before deployment
- **Consistency**: Same process every time
- **Fast feedback**: Catch issues early
- **Rollback**: Easy to revert bad deployments

### GitHub Actions Example

See [`.github/workflows/deploy.yml`](./.github/workflows/deploy.yml):

```yaml
name: Deploy Agent

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: pytest tests/ --cov=agenkit --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            myregistry/my-agent:latest
            myregistry/my-agent:${{ github.sha }}
          cache-from: type=registry,ref=myregistry/my-agent:latest
          cache-to: type=inline

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG }}

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/agenkit-agent \
            agent=myregistry/my-agent:${{ github.sha }} \
            -n agenkit

          kubectl rollout status deployment/agenkit-agent -n agenkit

      - name: Verify deployment
        run: |
          kubectl get pods -n agenkit
          kubectl get services -n agenkit
```

### CI/CD Best Practices

1. **Test before deploy**: Run comprehensive test suite
2. **Build once, deploy many**: Same artifact dev → staging → prod
3. **Automatic rollback**: Detect and revert failures
4. **Canary deployments**: Roll out to subset of users first
5. **Blue-green deployments**: Zero downtime updates
6. **Secrets management**: Never commit secrets, use CI/CD secrets

---

## 5. Monitoring: Observability Stack

### Why Monitoring?

- **Visibility**: Know what's happening
- **Alerting**: Detect issues early
- **Debugging**: Diagnose problems
- **Performance**: Optimize based on data
- **SLO tracking**: Meet reliability targets

### Monitoring Stack

**Prometheus** - Metrics collection
**Grafana** - Visualization
**Jaeger** - Distributed tracing
**ELK Stack** - Log aggregation

### Prometheus Configuration

See [`prometheus.yml`](./prometheus.yml):

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'agenkit-agent'
    static_configs:
      - targets: ['agent:8000']
    metrics_path: '/metrics'

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
```

### Instrumenting Your Agent

```python
from agenkit import Agent, Message
from agenkit.observability import MetricsMiddleware, TracingMiddleware
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
REQUEST_COUNT = Counter('agent_requests_total', 'Total agent requests', ['agent', 'status'])
REQUEST_DURATION = Histogram('agent_request_duration_seconds', 'Request duration', ['agent'])
ACTIVE_REQUESTS = Gauge('agent_active_requests', 'Active requests', ['agent'])

class MyAgent(Agent):
    def name(self) -> str:
        return "my-agent"

    async def process(self, message: Message) -> Message:
        # Your logic
        return Message(role="assistant", content="Response")

# Add observability middleware
agent = MyAgent()
agent = MetricsMiddleware(agent, prefix="agenkit_")
agent = TracingMiddleware(agent, service_name="my-agent")

# Expose metrics endpoint
from prometheus_client import make_asgi_app
from starlette.applications import Starlette
from starlette.routing import Mount

app = Starlette(routes=[
    Mount('/metrics', make_asgi_app()),
    # Your agent routes...
])
```

### Grafana Dashboards

See [`grafana-dashboard.json`](./grafana-dashboard.json) for pre-built dashboard.

Key metrics to monitor:

- **Request rate** - Requests per second
- **Error rate** - Errors per second
- **Latency** - P50, P95, P99 response times
- **Throughput** - Messages processed per second
- **Resource usage** - CPU, memory, network
- **LLM metrics** - Tokens used, cost, rate limits

### Alerting Rules

```yaml
# prometheus-alerts.yml
groups:
  - name: agenkit-alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(agent_requests_total{status="error"}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} requests/sec"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(agent_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }} seconds"

      - alert: AgentDown
        expr: up{job="agenkit-agent"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Agent is down"
          description: "Agent {{ $labels.instance }} is not responding"
```

---

## 6. Best Practices

### Security

```yaml
# Security best practices

# 1. Non-root user in Dockerfile
FROM python:3.11-slim
RUN useradd -m -u 1000 appuser
USER appuser

# 2. Read-only filesystem
securityContext:
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000

# 3. Network policies
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent-network-policy
spec:
  podSelector:
    matchLabels:
      app: agenkit-agent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379

# 4. Secrets management
# Use external secrets operator or cloud provider secrets
```

### Scaling

```python
# Scaling strategies

# 1. Horizontal scaling (more pods)
kubectl scale deployment agenkit-agent --replicas=10

# 2. Vertical scaling (more resources per pod)
# Update deployment.yaml:
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"

# 3. Autoscaling (dynamic)
# See HPA configuration above

# 4. Load testing
from locust import HttpUser, task, between

class AgentUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def process_message(self):
        self.client.post("/process", json={
            "role": "user",
            "content": "Hello!"
        })

# Run: locust -f locustfile.py --host=http://localhost:8000
```

### Reliability

```yaml
# Reliability best practices

# 1. Pod disruption budget
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: agenkit-agent-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: agenkit-agent

# 2. Liveness and readiness probes
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

# 3. Resource limits
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"

# 4. Graceful shutdown
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 15"]
terminationGracePeriodSeconds: 30
```

---

## 7. Complete Example

### Project Structure

```
my-agent/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── app.py
├── .dockerignore
├── .github/
│   └── workflows/
│       └── deploy.yml
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   └── hpa.yaml
├── prometheus.yml
├── grafana-dashboard.json
└── tests/
    ├── test_agent.py
    └── test_integration.py
```

### Development Workflow

```bash
# 1. Local development
python app.py

# 2. Test with Docker
docker build -t my-agent:dev .
docker run -p 8000:8000 my-agent:dev

# 3. Test with Docker Compose
docker-compose up -d
docker-compose logs -f

# 4. Run tests
pytest tests/

# 5. Commit and push (triggers CI/CD)
git add .
git commit -m "feat: Add new agent feature"
git push origin main

# 6. Monitor deployment
kubectl get pods -n agenkit
kubectl logs -f deployment/agenkit-agent -n agenkit

# 7. Check metrics
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana
```

---

## Resources

### Documentation
- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

### Tools
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [helm](https://helm.sh/) - Kubernetes package manager
- [kustomize](https://kustomize.io/) - Kubernetes configuration management
- [k9s](https://k9scli.io/) - Kubernetes CLI UI
- [dive](https://github.com/wagoodman/dive) - Docker image analyzer

### Examples
- [Kubernetes Examples](https://github.com/kubernetes/examples)
- [Awesome Docker](https://github.com/veggiemonk/awesome-docker)
- [Awesome Kubernetes](https://github.com/ramitsurana/awesome-kubernetes)

---

## Next Steps

- **[Testing Patterns Guide](../05-testing-patterns.md)** - Comprehensive testing strategies
- **[Production Examples](https://github.com/scttfrdmn/agenkit/tree/main/examples/apps)** - Real-world deployments
- **[API Documentation](https://agenkit.dev/api/)** - Complete API reference

## Troubleshooting

### Common Issues

**Docker build fails:**
```bash
# Clear cache and rebuild
docker build --no-cache -t my-agent .
```

**Pod crashlooping:**
```bash
# Check logs
kubectl logs -f <pod-name> -n agenkit
kubectl describe pod <pod-name> -n agenkit

# Check resource limits
kubectl top pods -n agenkit
```

**High memory usage:**
```python
# Use memory profiling
import tracemalloc
tracemalloc.start()

# Your agent code...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

**Metrics not showing:**
```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus targets
open http://localhost:9090/targets
```

Ready to deploy to production! 🚀
