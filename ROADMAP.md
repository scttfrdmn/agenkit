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

**Status**: ✅ Infrastructure Complete | ⏳ Baseline Collection In Progress

**Completed**:
- ✅ Middleware overhead benchmarks (Python: 8 tests, Go: 10 tests)
- ✅ Composition pattern benchmarks (Python: 8 tests)
- ✅ Baseline documentation and methodology (BASELINES.md)
- ✅ Benchmark validation (Python: 12.16% retry overhead, Go: 72.96ns/op)

**Implementation**:
- Python: `benchmarks/test_middleware_overhead.py` (~520 lines)
- Python: `benchmarks/test_composition_overhead.py` (~700 lines)
- Go: `agenkit-go/benchmarks/middleware_overhead_test.go` (~350 lines)
- Docs: `benchmarks/BASELINES.md` (comprehensive baseline documentation)

**Remaining**:
- Transport protocol benchmarks (HTTP/1.1 vs HTTP/2 vs HTTP/3)
- Message size benchmarks (small, medium, large, streaming)
- Concurrent load benchmarks (1, 10, 100, 1000 connections)
- CI integration for regression detection

**Tools**: pytest (Python), testing.B (Go), benchmark comparison tools

### Additional Transports

#### WebSocket Transport
Bidirectional communication and better streaming.

**Why**: True bidirectional communication, better streaming performance, lower latency, browser compatibility.

**Features**:
- Automatic reconnection
- Ping/pong keepalive
- Message framing
- TLS support

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

#### Timeout Middleware
Prevent long-running requests from blocking resources.

**Features**:
- Configurable timeout per request
- Graceful cancellation
- Timeout metrics

**Trade-offs**: User experience vs resource protection

#### Batching Middleware
Combine multiple requests for efficiency.

**Features**:
- Configurable batch size and timeout
- Request aggregation
- Response disaggregation

**Trade-offs**: Latency vs throughput

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
