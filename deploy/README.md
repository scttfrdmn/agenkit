# Agenkit Deployment Guide

This directory contains Docker and Kubernetes deployment configurations for Agenkit.

## Docker Deployment

### Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed

### Quick Start with Docker Compose

```bash
# Start all services (agents + observability stack)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Available Services

| Service | Port | Description |
|---------|------|-------------|
| `python-http-agent` | 8080 | Python HTTP agent |
| `go-http-agent` | 8081 | Go HTTP agent |
| `python-grpc-agent` | 50051 | Python gRPC agent |
| `go-grpc-agent` | 50052 | Go gRPC agent |
| `jaeger` | 16686 | Jaeger UI for distributed tracing |
| `prometheus` | 9090 | Prometheus metrics dashboard |

### Building Individual Images

```bash
# Build Python image
docker build -f Dockerfile.python -t agenkit/python:0.1.0 .

# Build Go image
docker build -f Dockerfile.go -t agenkit/go:0.1.0 .
```

### Using Images in Your Own Applications

```dockerfile
# Python application
FROM agenkit/python:0.1.0
COPY my_agent.py /app/
CMD ["python", "/app/my_agent.py"]

# Go application
FROM agenkit/go:0.1.0 AS builder
COPY . /build
RUN cd /build && go build -o myagent
FROM alpine:3.19
COPY --from=builder /build/myagent /app/
CMD ["/app/myagent"]
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+ cluster
- `kubectl` configured
- NGINX Ingress Controller (optional, for ingress)
- Cert-Manager (optional, for TLS)
- Metrics Server (required for HPA)

### Quick Start

```bash
# Create namespace and apply all manifests
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/

# Check deployment status
kubectl get pods -n agenkit
kubectl get svc -n agenkit

# View logs
kubectl logs -n agenkit deployment/agenkit-python-http -f
```

### Available Resources

#### Core Resources

- `namespace.yaml` - Agenkit namespace
- `configmap.yaml` - Configuration for all agents
- `python-http-deployment.yaml` - Python HTTP agent deployment
- `python-http-service.yaml` - Python HTTP agent service
- `go-http-deployment.yaml` - Go HTTP agent deployment
- `go-http-service.yaml` - Go HTTP agent service

#### Optional Resources

- `ingress.yaml` - HTTP ingress (requires NGINX Ingress Controller)
- `hpa.yaml` - Horizontal Pod Autoscaler (requires Metrics Server)

### Production Deployment Checklist

#### 1. Update Configuration

Edit `kubernetes/configmap.yaml` to match your environment:

```yaml
data:
  log_level: "INFO"
  otel_exporter_otlp_endpoint: "http://your-jaeger:4317"
  agent_timeout: "30s"
```

#### 2. Update Ingress

Edit `kubernetes/ingress.yaml`:

```yaml
spec:
  tls:
  - hosts:
    - your-domain.com
  rules:
  - host: your-domain.com
```

#### 3. Configure Resource Limits

Adjust resource requests/limits in deployment manifests based on your workload:

```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

#### 4. Enable Autoscaling

Apply HPA manifests:

```bash
kubectl apply -f kubernetes/hpa.yaml
```

Monitor autoscaling:

```bash
kubectl get hpa -n agenkit
```

### Monitoring

#### View Agent Logs

```bash
# Python HTTP agent
kubectl logs -n agenkit deployment/agenkit-python-http -f

# Go HTTP agent
kubectl logs -n agenkit deployment/agenkit-go-http -f
```

#### Check Health

```bash
# Port-forward and check health endpoint
kubectl port-forward -n agenkit svc/agenkit-python-http 8080:8080
curl http://localhost:8080/health
```

#### View Metrics

```bash
# Port-forward Prometheus (if running in cluster)
kubectl port-forward -n agenkit svc/prometheus 9090:9090

# Access at http://localhost:9090
```

### Scaling

#### Manual Scaling

```bash
# Scale Python agents to 5 replicas
kubectl scale deployment -n agenkit agenkit-python-http --replicas=5

# Scale Go agents to 10 replicas
kubectl scale deployment -n agenkit agenkit-go-http --replicas=10
```

#### Autoscaling (HPA)

HPA is configured to scale based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)
- Min replicas: 3
- Max replicas: 10

```bash
# Watch HPA status
kubectl get hpa -n agenkit -w
```

### Troubleshooting

#### Pods not starting

```bash
# Check pod status
kubectl describe pod -n agenkit <pod-name>

# Check events
kubectl get events -n agenkit --sort-by='.lastTimestamp'
```

#### Service not accessible

```bash
# Check service endpoints
kubectl get endpoints -n agenkit

# Check service
kubectl describe svc -n agenkit agenkit-python-http
```

#### Image pull errors

Ensure images are built and available:

```bash
# Build and tag images
docker build -f Dockerfile.python -t agenkit/python:0.1.0 .
docker build -f Dockerfile.go -t agenkit/go:0.1.0 .

# Push to registry (if using remote cluster)
docker tag agenkit/python:0.1.0 your-registry/agenkit/python:0.1.0
docker push your-registry/agenkit/python:0.1.0
```

### Cleanup

```bash
# Delete all resources
kubectl delete namespace agenkit

# Or delete individual resources
kubectl delete -f kubernetes/
```

## Security Considerations

### Container Security

All containers run as non-root users (UID 1000):

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL
```

### Network Security

- Use Network Policies to restrict traffic between pods
- Enable TLS for all external endpoints
- Use cert-manager for automatic certificate management

### Secrets Management

Store sensitive data in Kubernetes Secrets:

```bash
kubectl create secret generic agenkit-secrets \
  -n agenkit \
  --from-literal=api-key=your-api-key
```

Reference in deployments:

```yaml
env:
- name: API_KEY
  valueFrom:
    secretKeyRef:
      name: agenkit-secrets
      key: api-key
```

## Performance Tuning

### Resource Optimization

Monitor resource usage and adjust limits:

```bash
# Check resource usage
kubectl top pods -n agenkit
kubectl top nodes
```

### Connection Pooling

Configure appropriate connection pool sizes for your workload in ConfigMap.

### Horizontal Scaling

Use HPA with custom metrics for application-specific scaling:

```yaml
metrics:
- type: Pods
  pods:
    metric:
      name: http_requests_per_second
    target:
      type: AverageValue
      averageValue: "1000"
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/agenkit/agenkit/issues
- Documentation: https://docs.agenkit.dev
