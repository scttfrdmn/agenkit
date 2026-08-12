# Production Infrastructure Examples

Comprehensive examples for deploying production-ready agent systems with:

- **Load Balancing**: Distribute requests across multiple agent backends
- **Health Monitoring**: Kubernetes-style probes (liveness, readiness, startup)
- **Enhanced Retry**: Jitter, error classification, budget awareness, backpressure
- **Observability**: Prometheus metrics, Grafana dashboards, alerts

Perfect for **30-hour autonomous agent deployments** requiring high availability.

---

## Quick Start

### Local Python Example

```bash
cd python
uv run python production_agent.py
```

Expected output:
```
INFO - Starting production agent system...
INFO - Waiting for startup checks...
INFO - System is healthy and ready!
INFO - Request 0: SUCCESS - agent-2 processed: Request 0
...
INFO - FINAL METRICS
INFO - Load Balancer:
INFO -   Total requests: 20
INFO -   Successful: 19
INFO -   Success rate: 95.0%
```

### Local Go Example

```bash
cd go
go run production_agent.go
```

### Docker Compose (Full Stack)

```bash
cd docker
docker-compose up -d

# View metrics
open http://localhost:9091  # Prometheus
open http://localhost:3000  # Grafana (admin/admin)
```

### Kubernetes Deployment

```bash
cd k8s
kubectl apply -f deployment.yaml
kubectl apply -f monitoring.yaml

# Check health
kubectl get pods -l app=agenkit
kubectl logs -f deployment/agenkit-production
```

---

## Architecture

### Component Stack

```
┌─────────────────────────────────────────────┐
│           Load Balancer                     │
│  ┌─────────────────────────────────────┐   │
│  │  Strategy: Least Connections        │   │
│  │  Health Checks: Enabled             │   │
│  │  Backends: 3 agents                 │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
┌─────────┐   ┌─────────┐   ┌─────────┐
│ Agent 1 │   │ Agent 2 │   │ Agent 3 │
│ + Retry │   │ + Retry │   │ + Retry │
└─────────┘   └─────────┘   └─────────┘
    ↓               ↓               ↓
┌─────────────────────────────────────────────┐
│           Health Checker                    │
│  ┌─────────────────────────────────────┐   │
│  │  Liveness: 10s interval             │   │
│  │  Readiness: 5s interval             │   │
│  │  Startup: 30s timeout               │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                    ↓
        ┌───────────────────────┐
        │  Prometheus Metrics   │
        │  /metrics endpoint    │
        └───────────────────────┘
```

### Load Balancing Strategies

1. **Round Robin**: Simple rotation through backends
2. **Least Connections**: Route to backend with fewest active requests
3. **Weighted**: Distribute based on backend capacity weights
4. **Random**: Random selection (useful for even load)

### Health Check Probes

Based on Kubernetes probe model:

- **Startup Probe**: Allows slow initialization (30s timeout)
  - Kubernetes won't check liveness/readiness until this passes
  - Prevents premature restarts during startup

- **Liveness Probe**: Is the process alive? (10s interval)
  - Failure triggers pod restart
  - Checks basic agent functionality

- **Readiness Probe**: Can it handle traffic? (5s interval)
  - Failure removes from service endpoints
  - Tests actual message processing

### Retry Strategies

**Jitter Types**:
- **Full**: `delay = random(0, base_delay)` - Spreads load maximally
- **Equal**: `delay = base_delay/2 + random(0, base_delay/2)` - Balanced
- **Decorrelated**: `delay = random(base, previous * 3)` - AWS style
- **None**: No jitter - deterministic backoff

**Error Classification**:
- **Transient**: Network hiccups (retry aggressively)
- **RateLimit**: 429 errors (long backoff)
- **Timeout**: Request timeouts (moderate retry)
- **ServerError**: 5xx errors (careful retry)
- **ClientError**: 4xx errors (don't retry)
- **Unknown**: Unclassified (use defaults)

**Budget Awareness**:
- Cost limits per hour
- Retry count limits per hour
- Prevents runaway costs

**Backpressure Detection**:
- Monitors recent failure rate
- Automatically throttles when system is struggling
- Prevents cascade failures

---

## Examples by Language

### Python

**File**: `python/production_agent.py` (~330 LOC)

**Features**:
- Async/await throughout
- Three simulated backends with varying failure rates
- Comprehensive metrics logging
- Prometheus export

**Run**:
```bash
cd python
uv run python production_agent.py
```

**Key Code**:
```python
# Create load balancer with retry-wrapped backends
load_balancer = LoadBalancer(
    agents=[retry_backend1, retry_backend2, retry_backend3],
    config=LoadBalancerConfig(
        strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
        health_check_enabled=True,
    ),
)

# Start health monitoring
health_checker = HealthChecker(load_balancer, health_config)
health_checker.start()

# Process requests
response = await load_balancer.process(message)
```

### Go

**File**: `go/production_agent.go` (~340 LOC)

**Features**:
- Goroutines for concurrent health checks
- Channel-based communication
- Idiomatic error handling

**Run**:
```bash
cd go
go run production_agent.go
```

**Key Code**:
```go
// Wrap backends with retry
retryBackend1 := infrastructure.NewEnhancedRetryDecorator(backend1, retryConfig)

// Create load balancer
loadBalancer := infrastructure.NewLoadBalancer(
    []core.Agent{retryBackend1, retryBackend2, retryBackend3},
    lbConfig,
)

// Start health checker
healthChecker := infrastructure.NewHealthChecker(loadBalancer, healthConfig)
healthChecker.Start()
defer healthChecker.Stop()
```

### TypeScript

**File**: `typescript/production-agent.ts`

**Run**:
```bash
cd typescript
npm install
npm run production-agent
```

### Rust

**File**: `rust/production_agent.rs`

**Run**:
```bash
cd rust
cargo run --example production_agent
```

### C++

**File**: `cpp/production_agent.cpp`

**Build & Run**:
```bash
cd cpp/build
cmake ..
make production_agent
./production_agent
```

### Zig

**File**: `zig/production_agent.zig`

**Run**:
```bash
cd zig
zig build run-production-agent
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.19+)
- kubectl configured
- Prometheus Operator (optional, for ServiceMonitor)

### Deploy

```bash
cd k8s

# Deploy application
kubectl apply -f deployment.yaml

# Deploy monitoring
kubectl apply -f monitoring.yaml

# Verify deployment
kubectl get pods -l app=agenkit
kubectl get svc agenkit-production
```

### Configuration

**deployment.yaml** includes:
- **Deployment**: 3 replicas with anti-affinity
- **Service**: ClusterIP with HTTP + metrics ports
- **PVC**: 10Gi for state persistence
- **PDB**: Minimum 2 pods available during disruptions
- **HPA**: Auto-scale 3-10 pods based on CPU/memory

**Startup Probe**:
```yaml
startupProbe:
  httpGet:
    path: /health/startup
    port: 8080
  periodSeconds: 10
  failureThreshold: 30  # 5 minutes total
```

**Liveness Probe**:
```yaml
livenessProbe:
  httpGet:
    path: /health/liveness
    port: 8080
  periodSeconds: 10
  failureThreshold: 3  # Restart after 30s
```

**Readiness Probe**:
```yaml
readinessProbe:
  httpGet:
    path: /health/readiness
    port: 8080
  periodSeconds: 5
  failureThreshold: 2  # Remove after 10s
```

### Monitoring

**monitoring.yaml** includes:
- **ServiceMonitor**: Prometheus Operator integration
- **PrometheusRule**: 12 alert rules for production monitoring
- **ConfigMap**: Grafana dashboard JSON

**Key Alerts**:
- `AgentUnhealthy`: Health checks failing for 2+ minutes
- `HighRetryRate`: Retry rate > 30% for 5 minutes
- `BackpressureDetected`: System throttling due to failures
- `UnhealthyBackends`: < 2 healthy backends available

### Accessing Services

```bash
# Port-forward to access locally
kubectl port-forward svc/agenkit-production 8080:80

# Test health endpoints
curl http://localhost:8080/health/liveness
curl http://localhost:8080/health/readiness
curl http://localhost:8080/metrics
```

---

## Docker Compose

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

### Start Stack

```bash
cd docker
docker-compose up -d
```

**Services**:
- **agent**: Production agent (port 8080, 9090)
- **prometheus**: Metrics collection (port 9091)
- **grafana**: Visualization (port 3000)
- **redis**: State persistence (port 6379)
- **load-generator**: Testing traffic (profile: testing)

### Access Services

```bash
# Agent API
curl http://localhost:8080/health/liveness

# Prometheus
open http://localhost:9091

# Grafana (admin/admin)
open http://localhost:3000
```

### Run Load Test

```bash
# Start load generator
docker-compose --profile testing up load-generator

# Watch metrics
docker-compose logs -f agent
```

### Stop Stack

```bash
docker-compose down
# Or with volume cleanup
docker-compose down -v
```

---

## Metrics Reference

### Load Balancer Metrics

```
# Total requests processed
agenkit_loadbalancer_total_requests_total

# Successful requests
agenkit_loadbalancer_successful_requests_total

# Failed requests
agenkit_loadbalancer_failed_requests_total

# Backend-specific request counts
agenkit_loadbalancer_backend_requests_total{backend_id="agent-1"}

# Number of healthy backends
agenkit_loadbalancer_healthy_backends

# Active connections per backend
agenkit_loadbalancer_active_connections{backend_id="agent-1"}
```

### Health Check Metrics

```
# Total health checks performed
agenkit_health_checks_total{probe="liveness"}

# Failed health checks
agenkit_health_check_failures_total{probe="readiness"}

# Health check duration (milliseconds)
agenkit_health_check_duration_ms{probe="startup"}

# Agent uptime (seconds)
agenkit_agent_uptime_seconds

# Health status (1=healthy, 0=unhealthy)
agenkit_agent_healthy
```

### Retry Metrics

```
# Total attempts (including retries)
agenkit_attempts_total

# Successful on first attempt
agenkit_successful_first_attempt_total

# Successful after retry
agenkit_successful_on_retry_total

# Failed after all retries
agenkit_failed_after_retries_total

# Total retries performed
agenkit_retry_total

# Jitter added (seconds)
agenkit_jitter_added_seconds

# Budget exceeded count
agenkit_budget_exceeded_total

# Backpressure detected count
agenkit_backpressure_detected_total

# Error class counts
agenkit_error_class_total{class="rate_limit"}
```

---

## Performance Tuning

### Load Balancer

**Strategy Selection**:
- **Development**: Round Robin (simplest)
- **Production**: Least Connections (best for varied workloads)
- **Specific capacities**: Weighted (when backends differ)
- **Stateless uniform load**: Random (lowest overhead)

**Health Check Tuning**:
```python
LoadBalancerConfig(
    health_check_interval_ms=5000,  # More frequent = faster failure detection
    health_check_timeout_ms=2000,  # Lower = faster marking unhealthy
    max_retries_per_backend=2,  # Higher = more fault tolerance
)
```

### Retry Configuration

**Aggressive (low latency priority)**:
```python
EnhancedRetryConfig(
    max_attempts=2,
    initial_backoff_ms=50,
    max_backoff_ms=1000,
    jitter_type="full",
)
```

**Conservative (cost priority)**:
```python
EnhancedRetryConfig(
    max_attempts=3,
    initial_backoff_ms=1000,
    max_backoff_ms=30000,
    enable_budget=True,
    max_cost_per_hour=100.0,
)
```

**Balanced (production)**:
```python
EnhancedRetryConfig(
    max_attempts=3,
    initial_backoff_ms=100,
    max_backoff_ms=5000,
    jitter_type="equal",
    enable_backpressure=True,
    backpressure_threshold=0.3,
)
```

### Health Checks

**Fast failure detection**:
```python
HealthCheckConfig(
    liveness_interval_ms=5000,  # Check every 5s
    liveness_failure_threshold=2,  # Mark dead after 10s
    readiness_interval_ms=2000,  # Check every 2s
    readiness_failure_threshold=3,  # Remove after 6s
)
```

**Stable (avoid flapping)**:
```python
HealthCheckConfig(
    liveness_interval_ms=30000,  # Check every 30s
    liveness_failure_threshold=5,  # Mark dead after 2.5min
    readiness_interval_ms=10000,  # Check every 10s
    readiness_failure_threshold=3,  # Remove after 30s
)
```

---

## Troubleshooting

### High Retry Rate

**Symptom**: `agenkit_retry_total` increasing rapidly

**Diagnosis**:
```bash
# Check error class distribution
curl http://localhost:9090/metrics | grep error_class

# Check backpressure
curl http://localhost:9090/metrics | grep backpressure
```

**Solutions**:
- Increase backend capacity
- Adjust retry backoff (longer delays)
- Enable/tune backpressure detection
- Check backend health

### Unhealthy Agents

**Symptom**: `agenkit_agent_healthy == 0`

**Diagnosis**:
```bash
# Check health endpoint directly
curl http://localhost:8080/health/liveness
curl http://localhost:8080/health/readiness

# Check logs
kubectl logs deployment/agenkit-production
```

**Solutions**:
- Increase health check timeout
- Adjust failure threshold (allow more failures)
- Check resource limits (CPU/memory)
- Investigate agent errors

### Load Imbalance

**Symptom**: Uneven `backend_requests_total` distribution

**Diagnosis**:
```bash
# Check strategy
kubectl describe deployment agenkit-production | grep LOAD_BALANCER_STRATEGY

# Check backend health
curl http://localhost:9090/metrics | grep healthy_backends
```

**Solutions**:
- Switch to `least_connections` strategy
- Verify all backends are healthy
- Check if backends have equal capacity
- Consider weighted strategy if capacities differ

### Budget Exceeded

**Symptom**: `agenkit_budget_exceeded_total` increasing

**Diagnosis**:
```bash
# Check retry config
kubectl get configmap agenkit-config -o yaml

# Check cost per request
curl http://localhost:9090/metrics | grep attempts
```

**Solutions**:
- Increase budget limits
- Reduce max_attempts
- Optimize backend to reduce failures
- Add more capacity to reduce retries

---

## Best Practices

### For 30-Hour Autonomous Agents

1. **Health Monitoring**:
   - Enable all three probe types
   - Set startup timeout ≥ 2 minutes for model loading
   - Use liveness for crash detection
   - Use readiness for traffic control

2. **Load Balancing**:
   - Deploy ≥ 3 backends for redundancy
   - Use `least_connections` for varied workloads
   - Enable health checks
   - Set reasonable timeouts (not too aggressive)

3. **Retry Logic**:
   - Enable backpressure detection (threshold: 0.3)
   - Use `equal` or `decorrelated` jitter
   - Set budget limits to prevent runaway costs
   - Configure per-error-class strategies

4. **Observability**:
   - Export Prometheus metrics
   - Set up Grafana dashboards
   - Configure alerts for critical conditions
   - Monitor trends over time

5. **Resource Limits**:
   - Set memory limits with headroom for spikes
   - Set CPU requests for scheduling
   - Use HPA for auto-scaling
   - Monitor resource usage patterns

6. **State Management**:
   - Use PVCs for state persistence
   - Configure Redis/external storage for checkpoints
   - Implement graceful shutdown (30s termination grace)
   - Backup critical state regularly

---

## Next Steps

- **Custom Backends**: Implement your own agent backends
- **LLM Integration**: Connect to OpenAI, Anthropic, or local models
- **State Persistence**: Add checkpointing with external storage
- **Multi-Region**: Deploy across regions with global load balancing
- **Advanced Monitoring**: Add distributed tracing, custom metrics

See [ARCHITECTURE.md](../../docs/ARCHITECTURE.md) for design principles.
