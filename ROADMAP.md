# Agenkit Roadmap

This document outlines the development roadmap for agenkit, organized by phases and milestones.

## Current Status (November 2025)

### ✅ Completed
- **HTTP/2 and HTTP/3 Support**: Full support for HTTP/1.1, HTTP/2 (h2c cleartext), and HTTP/3 over QUIC
- **Python Feature Parity**: Complete implementation of middleware, composition, and tools patterns
- **Test Coverage**: 208 Python tests, 136 Go tests
- **Comprehensive Examples**: 6 runnable examples with WHY explanations (~3,600 lines)
- **Pattern Documentation**: In-depth guides for middleware and composition patterns

---

## Phase 1: Documentation & Examples (v0.2.0) 📚
**Status**: In Progress | **Due**: December 2025

Focus: Complete documentation with WHY explanations and runnable examples for all patterns.

### Priority: High

#### [#30](https://github.com/scttfrdmn/agenkit/issues/30) Middleware Pattern Examples and Documentation
- [x] Retry middleware example with real-world scenarios
- [x] Metrics middleware example with observability use cases
- [x] MIDDLEWARE.md pattern guide
- [x] Go examples for middleware patterns
- [ ] Video tutorial for middleware patterns

**Why**: Help developers understand when and how to use middleware for production resilience and observability.

#### [#31](https://github.com/scttfrdmn/agenkit/issues/31) Composition Pattern Examples and Documentation
- [x] Sequential agent example with pipeline use cases
- [x] Parallel agent example with ensemble methods
- [x] Fallback agent example with HA patterns
- [x] Conditional agent example with routing scenarios
- [x] COMPOSITION.md pattern guide
- [x] Go examples for composition patterns
- [ ] Video tutorials for each pattern

**Why**: Demonstrate how to build complex multi-agent systems with clear trade-offs.

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
- Example: `examples/transport/websocket_example.py` (4 scenarios)
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

#### gRPC Transport
High-performance RPC with native streaming support.

**Why**: Better performance than HTTP/REST, native streaming, strong typing, code generation.

**Features**:
- Protobuf message definitions
- Bidirectional streaming
- Connection multiplexing
- Load balancing integration

**Trade-offs**: Additional complexity (protobuf), less universal than HTTP

### Additional Middleware

#### Caching Middleware
Reduce latency and cost by caching responses.

**Features**:
- Configurable cache keys
- TTL-based expiration
- LRU eviction
- Cache invalidation

**Trade-offs**: Memory usage vs latency reduction, stale data risk

#### Timeout Middleware ✅
Prevent long-running requests from blocking resources.

**Status**: ✅ Complete (Python + Go + Benchmarks)

**Features**:
- ✅ Configurable timeout per request
- ✅ Graceful cancellation
- ✅ Timeout metrics
- ✅ Context-based cancellation (Go)
- ✅ asyncio.timeout integration (Python)

**Implementation**:
- Python: `agenkit/middleware/timeout.py` (13 tests)
- Go: `agenkit-go/middleware/timeout.go` (15 tests)
- Example: `examples/middleware/timeout_example.py`
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
- Go: `agenkit-go/middleware/batching.go` (12 tests, 340 lines)
- Example: `examples/middleware/batching_example.py` (5 scenarios)
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
**Status**: Ongoing

Focus: Comprehensive testing across all layers.

### Integration Tests
End-to-end tests across Go<->Python communication.

**Why**: Ensure cross-language compatibility, detect integration issues early.

**Coverage**:
- Cross-language agent communication
- All transport protocols
- Streaming scenarios
- Error handling

### Chaos Engineering Tests
Test resilience under failure conditions.

**Why**: Validate production resilience, identify weak points, build confidence.

**Scenarios**:
- Network failures (timeouts, connection drops)
- Service unavailability
- Slow responses
- Partial failures

### Property-Based Testing
Test invariants across many inputs.

**Why**: Find edge cases that unit tests miss, validate correctness properties.

**Tools**: Hypothesis (Python), rapid (Go)

---

## Phase 5: DevOps & Release (v1.0.0) 🔧
**Status**: Planned | **Due**: June 2026

Focus: Production deployment, Docker, Kubernetes, observability.

### Docker Images
Official Docker images for easy deployment.

**Why**: Simplified deployment, consistent environments, container orchestration.

**Images**:
- Base images (Go, Python)
- Example images (demos, tutorials)
- Multi-arch support (amd64, arm64)

### Kubernetes Deployment
Production-ready Kubernetes manifests.

**Why**: Cloud-native deployment, scaling, service discovery, health checks.

**Resources**:
- Deployment manifests
- Service definitions
- ConfigMaps for configuration
- Helm charts

### Observability
OpenTelemetry integration for tracing and metrics.

**Why**: Production debugging, performance analysis, SLA monitoring, distributed tracing.

**Features**:
- Distributed tracing
- Metrics export (Prometheus)
- Logging integration
- Span context propagation

---

## Phase 6: Community & Polish (v1.0.0) 🌟
**Status**: Planned | **Due**: June 2026

Focus: Community building, documentation polish, release preparation.

### Release Preparation
- [x] Version 0.1.0 initial release
- [ ] Version 0.2.0 (Documentation & Examples)
- [ ] Version 0.3.0 (Production Hardening)
- [ ] Version 0.4.0 (Performance & Features)
- [ ] Version 1.0.0 production release

### Documentation
- [ ] Contributing guidelines
- [ ] Code of conduct
- [ ] Security policy
- [ ] Issue/PR templates
- [ ] Compatibility matrix

### Marketing & Community
- [ ] Blog post series
- [ ] Conference talks
- [ ] Tutorial videos
- [ ] Community Discord/Slack
- [ ] X/Twitter presence

---

## Phase 7: Language Ports (v1.1.0+) 🌍
**Status**: Future

Focus: Extend to other popular languages while maintaining protocol compatibility.

### TypeScript/JavaScript
**Why**: Browser support, Node.js ecosystem, large developer base.

**Challenges**: Async patterns, type safety, package management.

### Rust
**Why**: Performance, memory safety, systems programming.

**Challenges**: Async runtime (tokio), error handling, FFI bindings.

### Java/JVM
**Why**: Enterprise adoption, Spring ecosystem, Android.

**Challenges**: Thread model, GC impact, verbosity.

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

- **Phase 2: Protocol Adapters** - 29% complete (2/7)
- **Phase 3: Framework Components** - 0% complete (0/7)
- **Phase 4: Documentation & Tools** - In Progress
- **Phase 5: Launch** - 0% complete (0/6)

---

## Questions or Feedback?

- 📧 Email: [your-email]
- 💬 Discussions: [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)
- 🐛 Issues: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
- 🐦 Twitter/X: [@agenkit]

Last updated: November 10, 2025
