# Agenkit Roadmap

This document outlines the development roadmap for agenkit, organized by phases and milestones.

## Current Status (November 2025)

### 🚀 Strategic Context: The Year Agents Went to Production

**November 2025** marks a watershed moment for AI agents:

1. **30-Hour Autonomous Operation**: Claude Sonnet 4.5 can work independently for 30+ hours
2. **Deep Reasoning**: OpenAI o3, Claude 4 Opus with extended thinking modes
3. **Production Reality**: AutoGen, LangGraph deployed in production at scale
4. **Tool-Use Evolution**: Models use tools during reasoning (not just sequential)

**Agenkit's 2026 Mission:** Provide minimal, composable interfaces for **production-scale autonomous agents**.

**Key Challenges:**
- **Memory**: 30-hour sessions exceed even 200K context windows
- **Cost**: Reasoning models expensive (o3: $5-15/1M, Opus 4: $15-75/1M)
- **Durability**: Long-running agents need checkpointing and resume
- **Safety**: Autonomous agents need guardrails (prompt injection, resource limits)
- **Evaluation**: How to measure 30-hour agent success?

See [.github/STRATEGIC_2026_ROADMAP.md](.github/STRATEGIC_2026_ROADMAP.md) for comprehensive 2026 strategy.

### ✅ Completed (Phases 1-5)
- **HTTP/2 and HTTP/3 Support**: Full support for HTTP/1.1, HTTP/2 (h2c cleartext), and HTTP/3 over QUIC
- **Python-Go Feature Parity**: ✅ Complete implementation parity across middleware, examples, and transports
- **Go LLM Adapters**: ✅ OpenAI and Anthropic support (#58, completed Nov 2025)
- **Test Coverage**: 278 Python tests, 181 Go tests (459 total)
  - Observability: 25 Python tests, 28 Go tests (53 tests)
  - Caching: 17 tests in both languages
- **Comprehensive Examples**: 12 runnable examples with WHY explanations (~6,700 lines)
  - Python: 6 middleware + 2 transport examples
  - Go: 7 middleware + 2 transport examples
- **Pattern Documentation**: In-depth guides for middleware and composition patterns
- **Observability**: Full OpenTelemetry integration with distributed tracing, metrics, and structured logging
- **Community Infrastructure**: Contributing guidelines, code of conduct, issue templates

---

## Phase 1: Documentation & Examples (v0.2.0) 📚
**Status**: ✅ Complete | **Completed**: November 2025

Focus: Complete documentation with WHY explanations and runnable examples for all patterns.

**Note**: Video tutorials have been deferred to a future phase (post-v1.0).

### Priority: High

#### [#30](https://github.com/scttfrdmn/agenkit/issues/30) Middleware Pattern Examples and Documentation
- [x] Retry middleware example with real-world scenarios
- [x] Metrics middleware example with observability use cases
- [x] MIDDLEWARE.md pattern guide
- [x] Go examples for middleware patterns

**Why**: Help developers understand when and how to use middleware for production resilience and observability.

**Status**: ✅ Complete

#### [#31](https://github.com/scttfrdmn/agenkit/issues/31) Composition Pattern Examples and Documentation
- [x] Sequential agent example with pipeline use cases
- [x] Parallel agent example with ensemble methods
- [x] Fallback agent example with HA patterns
- [x] Conditional agent example with routing scenarios
- [x] COMPOSITION.md pattern guide
- [x] Go examples for composition patterns

**Why**: Demonstrate how to build complex multi-agent systems with clear trade-offs.

**Status**: ✅ Complete

#### [#32](https://github.com/scttfrdmn/agenkit/issues/32) Tools/Function Calling Examples and Documentation
- [x] Calculator tool example
- [x] Search tool example
- [x] Database tool example
- [x] OS tools example (files, shell, git, editing, processes)
- [x] TOOLS.md guide
- [x] Go examples for tools
- [x] Security best practices documentation

**Why**: Show how tools extend agent capabilities with deterministic operations.

---

## Phase 2: Production Hardening (v0.3.0) 🛡️
**Status**: ✅ Completed | **Completed**: November 2025

Focus: Production-ready middleware and CI/CD infrastructure with test parity.

### ✅ Completed

#### Circuit Breaker Middleware
Prevent cascading failures in distributed systems.

**Implementation**: `agenkit/middleware/circuit_breaker.py`, `agenkit-go/middleware/circuit_breaker.go`

**Features**:
- Three states: CLOSED, OPEN, HALF_OPEN for intelligent failure handling
- Configurable failure threshold, recovery timeout, success threshold
- Request timeout handling
- Comprehensive metrics tracking
- Thread-safe implementation (asyncio.Lock, sync.Mutex)
- **Test parity**: 8 tests in Python, 8 tests in Go ✅

**Why it matters**: Protects systems from cascading failures by failing fast when services are unhealthy, allowing time for recovery.

#### Rate Limiting Middleware
Control request throughput and prevent API quota exhaustion.

**Implementation**: `agenkit/middleware/rate_limiter.py`, `agenkit-go/middleware/rate_limiter.go`

**Features**:
- Token bucket algorithm with configurable rate and burst capacity
- Automatic token refill over time
- Wait-based throttling (blocks until tokens available)
- Comprehensive metrics tracking
- Thread-safe implementation (asyncio.Lock, sync.Mutex)
- **Test parity**: 8 tests in Python, 8 tests in Go ✅

**Why it matters**:
- Protects downstream services from overload
- Complies with API rate limits (OpenAI: 3500 RPM, Anthropic: 50 RPM)
- Fair resource allocation across tenants
- Cost control

#### CI/CD Pipeline (GitHub Actions)
Automate testing, linting, and release processes with test parity enforcement.

**Implementation**: `.github/workflows/test.yml`, `.github/workflows/lint.yml`

**Features**:
- **Test Workflow**: Multi-OS (Ubuntu, macOS, Windows), multi-version testing
  - Python 3.10-3.12, Go 1.21-1.22
  - Automatic test parity checking (warns if >30% divergence)
  - Coverage upload to Codecov
  - PR comments with parity reports
- **Lint Workflow**: Comprehensive code quality checks
  - Python: Ruff, Black, isort, MyPy
  - Go: golangci-lint, go vet, go fmt, staticcheck
  - Security scanning: Trivy, Bandit, gosec
  - Dependency checking, license verification

**Why it matters**: Catches bugs early, ensures code quality, enforces test parity between languages.

### Priority: Low (Future Consideration)

#### Authentication & Authorization Examples
Show users how to integrate their own auth when needed.

**Rationale**: Auth is highly application-specific and users typically have existing auth infrastructure. Rather than building opinionated auth middleware, we'll provide examples showing how to write custom auth middleware for common patterns.

**Potential Examples** (low priority):
- API key validation middleware
- JWT verification middleware
- Integration with existing auth systems

**Why low priority**: Not core to agenkit's mission (agent patterns, composition, transport). Users can implement their own auth middleware using the established decorator pattern

---

## Phase 3: Performance & Features (v0.4.0) ⚡
**Status**: In Progress | **Due**: March 2026

Focus: Performance optimization, benchmarks, and additional transport protocols.

### Performance Benchmarking
Establish baselines and regression tests.

**Why**: Understand overhead, compare protocols, detect regressions, guide optimization.

**Status**: ✅ Complete (Benchmarks + CI Integration)

**Completed**:
- ✅ Middleware overhead benchmarks (Python: 8 tests, Go: 10 tests)
- ✅ Composition pattern benchmarks (Python: 8 tests)
- ✅ Transport protocol benchmarks (Python: 9 tests, Go: 23 tests) - HTTP/1.1, HTTP/2, and HTTP/3 ✅
- ✅ Message size benchmarks (small 100B, medium 10KB, large 1MB)
- ✅ Concurrent load benchmarks (1, 10, 50, 100 concurrent requests)
- ✅ Baseline documentation and methodology (BASELINES.md)
- ✅ Benchmark validation and cross-language comparison
- ✅ HTTP/3 over QUIC benchmarks with TLS (7 comprehensive tests)
- ✅ Streaming response benchmarks (Python: 8 tests, Go: 11 tests) ✅
- ✅ Python vs Go streaming performance comparison ✅
- ✅ CI integration with GitHub Actions (automated regression detection)
- ✅ HTTP/3 in CI with mkcert-generated TLS certificates
- ✅ Automated PR comments with benchmark comparison reports
- ✅ Benchstat integration for statistical significance testing

**Implementation**:
- Python: `benchmarks/test_middleware_overhead.py` (~520 lines)
- Python: `benchmarks/test_composition_overhead.py` (~700 lines)
- Python: `benchmarks/test_transport_overhead.py` (~583 lines) ✅
- Python: `benchmarks/test_streaming_overhead.py` (~600 lines) ✅
- Go: `agenkit-go/benchmarks/middleware_overhead_test.go` (~415 lines)
- Go: `agenkit-go/benchmarks/transport_overhead_test.go` (~802 lines) ✅
- Go: `agenkit-go/benchmarks/streaming_overhead_test.go` (~550 lines) ✅
- CI: `.github/workflows/benchmarks.yml` (automated regression detection with PR comments)
- Docs: `benchmarks/BASELINES.md` (comprehensive baseline documentation with results)
- Docs: `benchmarks/CI_BENCHMARKS.md` (CI usage and interpretation guide)

**Key Results**:
- Go transport: 18.5x faster than Python (0.055ms vs 1.02ms avg latency)
- HTTP/1.1 vs HTTP/2: Minimal difference (<2%), protocol choice has minimal impact
- HTTP/3: 3.3x slower than HTTP/1.1 (0.181ms vs 0.055ms) due to TLS encryption overhead
- HTTP/3 concurrent performance: 21% faster than HTTP/1.1, excellent for parallel workloads
- Message size scaling: Good efficiency (10,000x size = 190x latency)
- Transport overhead: <1% of total time in realistic LLM workloads
- Go streaming overhead: 2-4x vs batch, HTTP/3 has lowest overhead (1.65x) ✅
- Python streaming overhead: 1.47x (HTTP/1.1), 0.83x (HTTP/2 - streaming faster than batch!) ✅
- Go streaming latency: ~502-504ms for 10 chunks @ 50ms delay (optimal performance) ✅
- Python streaming latency: ~513-524ms (comparable to Go) ✅
- Python HTTP/2 streaming: 17% faster than batch, async generator efficiency ✅
- HTTP/2 best memory efficiency for streaming (112KB vs 163KB HTTP/1.1) ✅

**Future Enhancements**:
- Performance dashboard for tracking benchmark trends over time (planned)

**Tools**: pytest (Python), testing.B (Go), benchmark comparison tools

### Additional Transports

#### WebSocket Transport ✅
Bidirectional communication and better streaming.

**Status**: ✅ Complete (Python + Go + Examples + Tests)

**Why**: True bidirectional communication, better streaming performance, lower latency, browser compatibility.

**Implementation**:
- Python: `agenkit/adapters/python/websocket_transport.py` (25 tests)
- Go: `agenkit-go/adapter/transport/websocket_transport.go` (13 tests)
- Python Example: `examples/transport/websocket_example.py` (4 scenarios)
- Go Example: `agenkit-go/examples/transport/websocket_example.go` (4 scenarios)
- Integration tests: `tests/adapters/python/test_websocket_integration.py` (11 tests)

**Features**:
- ✅ Automatic reconnection with exponential backoff
- ✅ Ping/pong keepalive mechanism
- ✅ Native WebSocket framing (no length prefixes needed)
- ✅ TLS support (ws:// and wss://)
- ✅ Binary message protocol
- ✅ Server and client support in LocalAgent and HTTPAgent
- ✅ Streaming support with async generators

**Libraries**:
- Python: `websockets>=12.0` (asyncio-native)
- Go: `github.com/gorilla/websocket v1.5.3` (industry standard)

**Trade-offs**: Stateful connection vs HTTP stateless, connection management complexity

#### gRPC Transport ✅
High-performance RPC with native streaming support.

**Status**: ✅ Complete (Python + Go + Examples + Tests)

**Why**: Better performance than HTTP/REST, native streaming, strong typing, code generation.

**Implementation**:
- Proto: `proto/agent.proto` (protobuf definitions)
- Python: `agenkit/adapters/python/grpc_transport.py` (29 tests)
- Python: `agenkit/adapters/python/grpc_server.py` (gRPC server)
- Go: `agenkit-go/adapter/transport/grpc_transport.go` (15 tests, 40 test cases)
- Go: `agenkit-go/adapter/grpc/grpc_server.go` (gRPC server)
- Go: `agenkit-go/proto/agentpb/` (generated stubs)
- Python Example: `examples/transport/grpc_example.py` (5 scenarios)
- Go Example: `agenkit-go/examples/transport/grpc_example.go` (5 scenarios)

**Features**:
- ✅ Protobuf message definitions with schema validation
- ✅ Unary RPC (Process) and streaming RPC (ProcessStream)
- ✅ HTTP/2 connection multiplexing
- ✅ Binary protocol with Protocol Buffers
- ✅ Strong typing and code generation
- ✅ Server and client support in both languages
- ✅ Metadata propagation
- ✅ Rich error handling with gRPC status codes
- ✅ grpc:// endpoint support (default port: 50051)

**Libraries**:
- Python: `grpcio>=1.60.0`, `protobuf>=4.25.0`, `grpcio-tools>=1.60.0`
- Go: `google.golang.org/grpc v1.76.0`, `google.golang.org/protobuf v1.36.10`

**Trade-offs**: Additional complexity (protobuf), less universal than HTTP, but better performance and type safety

### Additional Middleware

#### Caching Middleware ✅
Reduce latency and cost by caching responses.

**Status**: ✅ Complete (Python + Go + Tests + Examples)

**Features**:
- ✅ Configurable cache keys with custom key generator support
- ✅ TTL-based expiration with automatic cleanup
- ✅ LRU (Least Recently Used) eviction policy
- ✅ Cache invalidation (specific entries or entire cache)
- ✅ Comprehensive metrics (hits, misses, hit rate, evictions, invalidations)
- ✅ Thread-safe (asyncio.Lock in Python, sync.Mutex in Go)
- ✅ Efficient LRU implementation (OrderedDict in Python, container/list in Go)

**Implementation**:
- Python: `agenkit/middleware/caching.py` (17 tests, 267 lines)
- Go: `agenkit-go/middleware/caching.go` (17 tests, 456 lines)
- Python Example: `examples/middleware/caching_example.py` (6 scenarios)
- Go Example: `agenkit-go/examples/middleware/caching_example.go` (6 scenarios)
- Default key: SHA256 hash of role + content + metadata
- Custom key generators supported for specialized strategies

**Performance**:
- Cache hits: <1ms overhead (near-instant)
- Reduces LLM API calls and costs significantly
- Memory usage proportional to cache size (configurable)
- Periodic cleanup prevents memory leaks

**Use Cases**:
- Frequently repeated requests
- Deterministic or acceptable-stale responses
- Cost/latency optimization over freshness
- Traffic patterns with request locality

**Trade-offs**: Memory usage vs latency reduction, stale data risk (controlled by TTL)

#### Timeout Middleware ✅
Prevent long-running requests from blocking resources.

**Status**: ✅ Complete (Python + Go + Tests + Examples + Benchmarks)

**Features**:
- ✅ Configurable timeout per request
- ✅ Graceful cancellation
- ✅ Timeout metrics
- ✅ Context-based cancellation (Go)
- ✅ asyncio.timeout integration (Python)

**Implementation**:
- Python: `agenkit/middleware/timeout.py` (18 tests)
- Go: `agenkit-go/middleware/timeout.go` (15 tests)
- Python Example: `examples/middleware/timeout_example.py` (6 scenarios)
- Go Example: `agenkit-go/examples/middleware/timeout_example.go` (6 scenarios)
- Benchmarks: Added to middleware overhead suite (Python + Go)

**Performance**:
- Python: 295% overhead (2.1µs absolute), 7x faster than circuit breaker
- Go: 26% faster than Python in absolute terms (1.5µs vs 2.1µs)
- Production impact: <0.01% overhead on real LLM workloads

**Trade-offs**: User experience vs resource protection

#### Batching Middleware ✅
Combine multiple concurrent requests for efficiency.

**Status**: ✅ Complete (Python + Go + Benchmarks + Examples)

**Features**:
- ✅ Configurable batch size, wait time, and queue size
- ✅ Dual threshold (size OR timeout triggers batch)
- ✅ Automatic request aggregation with background processor
- ✅ Individual response distribution via futures/channels
- ✅ Partial failure handling
- ✅ Comprehensive metrics tracking

**Implementation**:
- Python: `agenkit/middleware/batching.py` (21 tests, 370 lines)
- Go: `agenkit-go/middleware/batching.go` (15 tests, 340 lines)
- Python Example: `examples/middleware/batching_example.py` (5 scenarios)
- Go Example: `agenkit-go/examples/middleware/batching_example.go` (5 scenarios)
- Benchmarks: Added to middleware overhead suite (Python + Go)

**Performance**:
- Python: ~318% overhead (~12µs absolute) for concurrent requests
- Go: ~1,663% overhead (~1.3µs absolute) - higher relative, lower absolute
- Production impact: <0.01% overhead on real LLM workloads (100-1000ms)
- Designed for throughput optimization, not latency minimization

**Real-World Benefits**:
- Cost savings: 50% reduction with batch API pricing (OpenAI Batch API)
- Throughput: 10-100x improvement for database bulk operations
- Efficiency: Reduced network round-trips and connection overhead

**Trade-offs**: Adds latency (max_wait_time) for better throughput and cost savings

---

## Phase 4: Testing & Quality (v0.4.0) ✅
**Status**: ✅ **100% Complete** (137/137 tests passing) | **Target**: December 2025

Focus: Comprehensive testing across all layers for production readiness.

**Summary**:
- ✅ Phase 4.1: Cross-Language Integration Tests - 47/47 passing (100%)
- ✅ Phase 4.2: Chaos Engineering Tests - 53/53 passing (100%)
- ✅ Phase 4.3: Property-Based Testing - 37/37 implemented (100%)

**Test Plan**: See [PHASE4_TEST_PLAN.md](docs/PHASE4_TEST_PLAN.md) for detailed test plan.

### Cross-Language Integration Tests ✅
End-to-end tests across Go<->Python communication.

**Status**: ✅ **Phase 4.1 Complete** (47/47 tests passing, 100% success rate)

**Why**: Ensure cross-language compatibility works in production, detect integration issues early.

**Completed** (47 tests):
- ✅ **HTTP Transport**: 18/18 tests (Python ↔ Go, both directions)
  - Basic messages, metadata, Unicode, large messages (1MB)
  - Concurrent requests (10, 50), HTTP/2, connection reuse
  - Error handling, health checks
- ✅ **WebSocket Transport**: 10/10 tests (Python ↔ Go, bidirectional)
  - Basic messages, metadata, Unicode, large messages
  - Multiple messages, concurrent connections, connection reuse
- ✅ **gRPC Transport**: 12/12 tests (Python ↔ Go, unary)
  - Basic messages, metadata, Unicode, large messages
  - Multiple messages, concurrent requests, connection reuse
- ✅ **Observability**: 7/7 tests (Issue #53 fully resolved!)
  - W3C Trace Context format validation ✅
  - Trace context extraction ✅
  - Trace propagation Python → Go HTTP (with span verification) ✅
  - Trace propagation Go → Python HTTP (with span verification) ✅
  - Trace propagation Python → Go gRPC (with span verification) ✅
  - Trace propagation Go → Python gRPC (with span verification) ✅
  - Metadata preservation with tracing ✅

**Implementation**:
- Python: `tests/integration/test_*_cross_language.py`
- Test Infrastructure: `tests/integration/helpers.py`
- Go Test Servers: `agenkit-go/tests/integration/test_*_server.go`

**Priority**: 🔴 Critical (Required for v1.0)

**Next Steps**: See Phase 4.2 (Chaos Engineering) and Phase 4.3 (Property-Based Testing)

### Chaos Engineering Tests ✅
Test resilience under failure conditions.

**Status**: ✅ **Phase 4.2 Complete** (53/53 tests passing)

**Why**: Validate production resilience claims, prove middleware works under chaos, build confidence for production use.

**Completed** (53 tests):
- ✅ **Middleware Resilience**: 12/12 tests
  - Retry with intermittent failures, backoff, exhaustion (4 tests)
  - Circuit breaker open/half-open/recovery, cascade prevention (3 tests)
  - Timeout with slow service, hang prevention (2 tests)
  - Combined middleware: retry + circuit breaker + timeout (3 tests)
- ✅ **Network Failures**: 11/11 tests
  - Connection timeouts, slow responses, retries (3 tests)
  - Connection refused scenarios (2 tests)
  - Connection drops and recovery (2 tests)
  - Intermittent connectivity patterns (2 tests)
  - Random errors + concurrent chaos (2 tests)
- ✅ **Partial Failures**: 10/10 tests
  - Request-level partial failures with retry (2 tests)
  - Stream failures mid-stream, intermittent, slow chunks, cancellation (4 tests)
  - Batch failures with timeouts (2 tests)
  - Graceful degradation scenarios (2 tests)
- ✅ **Service Unavailability**: 11/11 tests
  - Service crashes (immediate, after N requests, mid-request) (3 tests)
  - Startup/shutdown scenarios (graceful, rejects new requests) (3 tests)
  - Overload and recovery (queue full, cascade) (3 tests)
  - Flakey service patterns (2 tests)
- ✅ **Slow Responses**: 9/9 tests
  - Gradual performance degradation, tail latency spikes (3 tests)
  - Large payload handling (single, concurrent) (3 tests)
  - Sustained load performance (2 tests)
  - Timeout with degrading service (1 test)

**Implementation**:
- Python: `tests/chaos/test_*.py` (5 test modules, 53 tests)
- Infrastructure: `tests/chaos/chaos_agents.py`, `tests/chaos/helpers.py`
- Tools: Manual chaos injection (ChaoticAgent, ChaosMode)

**Priority**: ✅ Complete

### Property-Based Testing Enhancement ✅
Test invariants across many inputs.

**Status**: ✅ **Phase 4.3 Complete** (37/37 tests implemented)

**Why**: Find edge cases that unit tests miss, validate correctness properties, ensure robustness.

**Completed** (37 tests):
- ✅ **Cache Properties**: 8/8 tests (size bounds, hit rate, LRU ordering, TTL, idempotency, statistics, no duplicates)
- ✅ **Circuit Breaker Properties**: 8/8 tests (state transitions, thresholds, half-open behavior, reset, failure counts)
- ✅ **Message Properties**: 11/11 tests (round-trip consistency, type preservation, metadata, serialization, Unicode, determinism, idempotency)
- ✅ **Retry Properties**: 10/10 tests (count limits, backoff delays, success propagation, max delay, exponential growth, exception filtering)

**Implementation**:
- Python: `tests/property/test_*_properties.py` (4 modules, 37 tests with Hypothesis)
- Infrastructure: `tests/property/strategies.py` (custom Hypothesis strategies)
- Go: Property-based testing expansion planned for future

**Priority**: ✅ Complete

**Tools**: Hypothesis (Python), rapid or gopter (Go - planned)

---

## Phase 5: DevOps & Release (v1.0.0) 🔧
**Status**: ✅ **100% Complete** | **Due**: June 2026

Focus: Production deployment, Docker, Kubernetes, observability.

**Summary**:
- ✅ Observability - Complete (Python + Go + Tests + Documentation)
- ✅ Docker Images - Complete (Python, Go, multi-stage builds)
- ✅ Kubernetes Deployment - Complete (Manifests, HPA, Ingress, ConfigMaps)

### Observability ✅
OpenTelemetry integration for tracing and metrics.

**Status**: ✅ Complete (Python + Go + Tests + Documentation)

**Why**: Production debugging, performance analysis, SLA monitoring, distributed tracing.

**Implementation**:
- Python: `agenkit/observability/` (~900 lines)
- Go: `agenkit-go/observability/` (~1,100 lines)
- Python Tests: 25 tests (test_tracing.py, test_metrics.py, test_logging.py)
- Go Tests: 28 tests (tracing_test.go, metrics_test.go, logging_test.go)
- Documentation: `docs/observability.md`, `docs/observability-python-api.md`, `docs/observability-go-api.md`

**Features**:
- ✅ Distributed tracing with W3C Trace Context propagation
- ✅ Automatic span creation for agent processing
- ✅ Parent-child span relationships across agents and languages
- ✅ Prometheus metrics export (request counts, latencies, error rates, message sizes)
- ✅ Structured JSON logging with trace correlation
- ✅ TracingMiddleware and MetricsMiddleware for easy integration
- ✅ Configurable exporters (console, OTLP, Prometheus)
- ✅ Cross-language compatibility (Python ↔ Go trace continuity)

**Libraries**:
- Python: `opentelemetry-api>=1.20.0`, `opentelemetry-sdk>=1.20.0`
- Go: `go.opentelemetry.io/otel v1.32.0`

**Completed**: November 2025 (Issue #46)

### Docker Images ✅
Official Docker images for easy deployment.

**Status**: ✅ Complete

**Why**: Simplified deployment, consistent environments, container orchestration.

**Deliverables**:
- ✅ Python Dockerfile with multi-stage build (slim base, 3.11)
- ✅ Go Dockerfile with multi-stage build (Alpine base, 1.21)
- ✅ Docker Compose configuration with full stack:
  - Python HTTP/gRPC agents
  - Go HTTP/gRPC agents
  - Jaeger for distributed tracing
  - Prometheus for metrics
- ✅ .dockerignore for optimal build context
- ✅ Non-root user security (UID 1000)
- ✅ Health check endpoints
- ✅ Environment variable configuration

**Files**:
- `Dockerfile.python` - Python base image
- `Dockerfile.go` - Go base image
- `docker-compose.yml` - Full stack orchestration
- `.dockerignore` - Build optimization
- `deploy/prometheus.yml` - Metrics configuration

**Features**:
- Multi-stage builds for minimal image size
- Security best practices (non-root, read-only filesystem)
- OpenTelemetry integration for observability
- Health checks for container orchestration
- Volume mounts for configuration

### Kubernetes Deployment ✅
Production-ready Kubernetes manifests.

**Status**: ✅ Complete

**Why**: Cloud-native deployment, scaling, service discovery, health checks.

**Deliverables**:
- ✅ Namespace configuration
- ✅ ConfigMaps for environment configuration
- ✅ Deployments for Python and Go agents
- ✅ Service definitions (ClusterIP)
- ✅ Ingress configuration (NGINX)
- ✅ Horizontal Pod Autoscaler (HPA)
- ✅ Security contexts (non-root, no privilege escalation)
- ✅ Resource limits and requests
- ✅ Liveness and readiness probes
- ✅ Prometheus annotations for metrics scraping
- ✅ Comprehensive deployment documentation

**Files**:
- `deploy/kubernetes/namespace.yaml` - Namespace
- `deploy/kubernetes/configmap.yaml` - Configuration
- `deploy/kubernetes/python-http-deployment.yaml` - Python deployment
- `deploy/kubernetes/python-http-service.yaml` - Python service
- `deploy/kubernetes/go-http-deployment.yaml` - Go deployment
- `deploy/kubernetes/go-http-service.yaml` - Go service
- `deploy/kubernetes/ingress.yaml` - HTTP ingress
- `deploy/kubernetes/hpa.yaml` - Autoscaling
- `deploy/README.md` - Deployment guide

**Features**:
- Production-ready security (non-root, capabilities dropped)
- Autoscaling based on CPU/memory (3-10 replicas)
- Health checks (liveness + readiness)
- Resource limits (CPU + memory)
- Service mesh ready (Prometheus annotations)
- TLS support (cert-manager integration)
- Multi-environment support (ConfigMaps)

**Scaling**:
- Horizontal autoscaling: 3-10 replicas per deployment
- CPU target: 70% utilization
- Memory target: 80% utilization
- Scale-up: 2 pods or 100% every 30s
- Scale-down: 50% every 60s (5min stabilization)

---

## Phase 6: Autonomous Agents Foundation (v1.0.0) 🤖
**Status**: In Progress (Q4 2025) | **Due**: December 2025

**Context:** November 2025 - Agents can now run for 30+ hours autonomously (Claude Sonnet 4.5, OpenAI o3). New challenges: memory, cost, durability.

Focus: Core infrastructure for production-scale autonomous agents.

### Q4 2025 Priorities (Nov-Dec)

#### [#67](https://github.com/scttfrdmn/agenkit/issues/67) Memory Systems ✅ CRITICAL
- [ ] Memory interface (ABC) for pluggable storage
- [ ] InMemory, Redis, Vector implementations
- [ ] Integration with endless project (infinite context)
- [ ] Sliding window, summarization, importance weighting strategies
- [ ] ConversationalAgent with memory support

**Why**: 30-hour agents need persistent memory beyond context windows.

#### [#68](https://github.com/scttfrdmn/agenkit/issues/68) Cost Tracking & Budget Management ✅ CRITICAL
- [ ] CostTracker (per session, per agent, global)
- [ ] BudgetLimiter middleware (stop at threshold)
- [ ] ModelOptimizer (route based on complexity/cost)
- [ ] Model pricing data (current as of Nov 2025)

**Why**: Reasoning models expensive (o3: $5-15/1M, Opus 4: $15-75/1M). 30-hour runs could cost hundreds.

#### [#69](https://github.com/scttfrdmn/agenkit/issues/69) Long-Running Agent Pattern ✅ CRITICAL
- [ ] Checkpointing interface
- [ ] State persistence
- [ ] Resume from checkpoint
- [ ] Durable execution (LangGraph-style)

**Why**: Claude Sonnet 4.5 works for 30 hours autonomously. Need durability.

### Community & Documentation (Ongoing)

#### Documentation (✅ Done in Nov 2025)
- [x] Contributing guidelines (CONTRIBUTING.md)
- [x] Code of conduct (CODE_OF_CONDUCT.md)
- [x] Issue/PR templates
- [ ] Security policy (#66)
- [ ] Compatibility matrix (#66)

#### Release Preparation
- [x] Version 0.1.0-0.4.0 (complete)
- [ ] Version 1.0.0 production release (June 2026)

#### Marketing & Community (Future)
- [ ] Blog post series
- [ ] Conference talks
- [ ] Tutorial videos
- [ ] Community Discord/Slack
- [ ] X/Twitter presence

---

## Phase 7: Language Expansion (v1.1.0) 🌍
**Status**: Q1-Q3 2026 | **Due**: September 2026

Focus: TypeScript and Rust ports for web/edge computing.

### Q1 2026: TypeScript/JavaScript Port ✅ HIGH PRIORITY

#### [#70](https://github.com/scttfrdmn/agenkit/issues/70) TypeScript Implementation
- [ ] Core interfaces (Agent, Message, Tool)
- [ ] HTTP/WebSocket/gRPC transports
- [ ] Middleware system
- [ ] LLM adapters (OpenAI, Anthropic)
- [ ] npm package publication

**Why First**: Massive web developer market (LangChain.js mature but heavy - opportunity for minimal alternative).

**Market Size**: Node.js + browser agents + serverless functions.

### Q3 2026: Rust Port ✅ PERFORMANCE TIER

#### [#76](https://github.com/scttfrdmn/agenkit/issues/76) Rust Implementation (Planned)
- [ ] Core interfaces with Tokio async (4.5k req/sec proven)
- [ ] HTTP/WebSocket/gRPC transports
- [ ] LLM adapters
- [ ] Cargo package publication

**Why**: Edge computing, embedded agents, performance-critical systems.

**Differentiation**: 10-100x faster than Python for CPU-bound tasks.

### Future Consideration: Java/C# (Enterprise)
- **Java**: Spring Boot ecosystem, Android
- **C#**: .NET ecosystem, Azure integration
- **Timeline**: Post-v1.1 (based on demand)

---

## Phase 8: Advanced Patterns (v1.2.0) 🚀
**Status**: Q1-Q2 2026 | **Due**: June 2026

Focus: New agent patterns from 2025 research + production capabilities.

### Q1 2026: Safety & Reasoning

#### [#71](https://github.com/scttfrdmn/agenkit/issues/71) Agent Safety Framework ✅ HIGH PRIORITY
- [ ] Input validation (prompt injection defense)
- [ ] Output validation (schema, content filtering)
- [ ] Action constraints (sandboxing, permissions)
- [ ] Anomaly detection

**Why**: Autonomous agents need guardrails. Research: "prompt injection = complete control."

#### [#72](https://github.com/scttfrdmn/agenkit/issues/72) Reasoning Budget Pattern ✅ NEW IN 2025
- [ ] Dynamic allocation (instant vs extended thinking)
- [ ] Complexity detection
- [ ] Model router (o3 for hard, Sonnet for medium, Haiku for simple)
- [ ] Cost-quality tradeoff

**Why**: Hybrid models (Claude 4, o3) have dual modes. Need orchestration.

### Q2 2026: Evaluation & Routing

#### [#73](https://github.com/scttfrdmn/agenkit/issues/73) Evaluation Framework ✅ CRITICAL GAP (Planned)
- [ ] Success/failure metrics
- [ ] Session replay
- [ ] Regression detection
- [ ] A/B testing for agents

**Why**: How do you know 30-hour agent succeeded? Need measurement.

#### [#74](https://github.com/scttfrdmn/agenkit/issues/74) Routing & Semantic Tool Selection (Planned)
- [ ] Semantic tool selection (inspired by AWS AgentCore Gateway)
- [ ] Load balancer (route to least-loaded agent)
- [ ] Enhanced circuit breaker
- [ ] MCP protocol support

**Why**: Production systems have hundreds of tools. Need intelligent routing.

#### [#75](https://github.com/scttfrdmn/agenkit/issues/75) Tool-Use During Reasoning Pattern (Planned)
- [ ] Interleaved reasoning + tool calls
- [ ] Different from ReAct (reasoning inside tool selection)
- [ ] Support for Claude 4 / o3 style

**Why**: Claude 4: "Use tools during extended thinking." New capability.

#### Complete Core Agent Patterns
- [ ] Implement #64 (Agent Pattern Implementations)
- [ ] Implement #65 (End-to-End Examples)
- [ ] Implement #66 (Security & Compatibility)

---

## Contributing to the Roadmap

We welcome community input on our roadmap! Here's how to contribute:

1. **Vote on existing issues**: Use 👍 reactions to vote for features you want
2. **Propose new features**: Open an issue with the `enhancement` label
3. **Discuss trade-offs**: Comment on issues to discuss design decisions
4. **Submit PRs**: Implement features and link them to roadmap issues

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## Milestone Tracking

Track progress on our [GitHub Milestones](https://github.com/scttfrdmn/agenkit/milestones):

- **Phase 1: Documentation & Examples (v0.2.0)** - ✅ 100% complete
- **Phase 2: Production Hardening (v0.3.0)** - ✅ 100% complete
- **Phase 3: Performance & Features (v0.4.0)** - ✅ 100% complete
- **Phase 4: Testing & Quality (v0.4.0)** - ✅ 100% complete (137/137 tests passing)
- **Phase 5: DevOps & Release (v1.0.0)** - ✅ 100% complete (Docker + Kubernetes + Observability)
- **Phase 6: Autonomous Agents Foundation (v1.0.0)** - 🔄 In Progress (Q4 2025 - memory, cost, durability)
- **Phase 7: Language Expansion (v1.1.0)** - 📋 Planned (Q1-Q3 2026 - TypeScript, Rust)
- **Phase 8: Advanced Patterns (v1.2.0)** - 📋 Planned (Q1-Q2 2026 - safety, evaluation, routing)

### 2026 Strategic Priorities

**Q4 2025 (Now):** Memory, Cost Tracking, Long-Running Agents (#67-69)
**Q1 2026:** TypeScript Port, Safety Framework, Reasoning Budget (#70-72)
**Q2 2026:** Evaluation, Routing, Tool-Use During Reasoning (#73-75)
**Q3 2026:** Rust Port, Advanced Memory, Reference Architectures (#76-78)

See [.github/STRATEGIC_2026_ROADMAP.md](.github/STRATEGIC_2026_ROADMAP.md) for detailed 2026 strategy.

### Deferred Items
- **Video Tutorials**: Deferred to post-v1.0 (middleware, composition, and tool usage tutorials)

---

## Questions or Feedback?

- 📧 Email: [your-email]
- 💬 Discussions: [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)
- 🐛 Issues: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
- 🐦 Twitter/X: [@agenkit]

Last updated: November 13, 2025 (Updated with 2026 strategic roadmap)
