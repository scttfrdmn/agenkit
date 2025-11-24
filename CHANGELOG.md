# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.10.0] - 2025-11-23

### 🚀 Phase 7 & 8 Complete - Advanced Patterns, Security, and Performance

This release completes Phases 7 (Language Expansion) and 8 (Advanced Patterns), delivering TypeScript support, advanced agent patterns, comprehensive security framework, and significant performance improvements. The framework is now feature-complete and ready for production deployment at scale.

**Key Highlights:**
- ✅ **Phase 7 Complete**: TypeScript implementation with 98 tests (ready for npm publication)
- ✅ **Phase 8 Complete**: Advanced patterns, safety framework, reasoning budget support
- ✅ **5 Complete End-to-End Applications**: Production-ready reference implementations
- ✅ **Security Hardened**: Auth/authz, TLS, input validation, error sanitization
- ✅ **Performance Optimized**: Connection pooling (20-35% faster), async read-write locks
- ✅ **Observability Enhanced**: Prometheus alerts, SLOs, resource metrics

### Added

#### Phase 7: Language Expansion (#70)

**TypeScript Implementation** ✅
- Complete TypeScript port with full feature parity (Python/Go)
- 98 tests passing (100% pass rate)
- All 3 transports: HTTP, WebSocket, gRPC
- Middleware system: Retry, Timeout, Circuit Breaker
- LLM adapters: OpenAI and Anthropic
- 4 comprehensive examples (~550 lines)
- Ready for npm publication as `@agenkit/core v0.2.0`

**Why TypeScript**: Massive web developer market, serverless functions, browser agents, Node.js ecosystem

#### Phase 8: Advanced Patterns

**Issue #71: Agent Safety Framework** ✅ COMPLETE
- **Input Validation**: Prompt injection defense, malicious input detection
  - Pattern-based detection (SQL injection, XSS, path traversal)
  - Length limits and character whitelisting
  - Semantic analysis for jailbreak attempts
- **Output Validation**: Schema validation, content filtering, PII detection
  - JSON schema validation
  - Profanity and sensitive data filtering
  - Custom validation rules
- **Action Constraints**: Sandboxing, permissions, resource limits
  - File system access control
  - Network restrictions
  - Command execution sandboxing
- **Anomaly Detection**: Behavioral monitoring, rate limiting
  - Request pattern analysis
  - Unusual activity detection
- **Audit Logging**: Comprehensive security event logging
  - Request/response logging with trace IDs
  - Security event tracking
  - Tamper-evident logs
- **Implementation**: Python (162 tests) + Go (94 tests) = 256 total tests
- **Examples**: 6 practical security scenarios (Python + Go)
- **Documentation**: Comprehensive docs/safety.md guide

**Issue #72: Reasoning Budget Pattern** ✅ COMPLETE
- **Dynamic Thinking Budget Allocation**: Instant vs extended thinking
  - `ThinkingBudgetAllocator` for adaptive budget management
  - Complexity-aware budget allocation
- **Complexity Detection**: Task difficulty analysis
  - `ComplexityDetector` for task analysis
  - `ThinkingModeDetector` for mode recommendation
- **Model Router**: Intelligent model selection
  - `ModelOptimizer.complete_with_thinking()`
  - Route to o3 (hard), Claude 4 Sonnet (medium), Haiku (simple)
- **Cost-Quality Tradeoff**: Budget-aware thinking mode selection
  - Extended `CostTracker` with `thinking_tokens` field
  - Cost projection and optimization
- **Support**: OpenAI o3, Claude 4 extended thinking modes
- **Implementation**: 21 tests for extended thinking patterns
- **Example**: `examples/budget/extended_thinking_demo.py`
- **Documentation**: Extended BUDGET.md with thinking budget section

**Issue #74: Advanced Agent Patterns** ✅ COMPLETE
- **Conversational Agent**: Stateful conversation with memory
  - Message history management
  - Context window handling
  - Memory integration
- **ReAct Agent**: Reasoning + Acting loop
  - Think → Act → Observe cycle
  - Tool integration
  - Reflection and planning
- **Planning Agent**: Task decomposition and execution
  - Hierarchical task planning
  - Subtask execution
  - Dynamic replanning
- **Multi-Agent**: Collaborative agent systems
  - Agent coordination
  - Message passing
  - Consensus building
- **Autonomous Agent**: Long-running agents with checkpointing
  - State persistence
  - Resume capability
  - Error recovery
- **Implementation**: Complete Python + Go implementations
- **Tests**: Comprehensive test coverage
- **Examples**: 5 pattern examples demonstrating each

**Issue #75: End-to-End Application Examples** ✅ COMPLETE

Five production-ready reference applications:

1. **Customer Support System** 🎧
   - Router → [FAQ, Docs, Specialist, Human]
   - Cross-language (Python router + Go specialists)
   - LLM integration (OpenAI/Anthropic)
   - Tools: Database, search, ticketing
   - Middleware: Retry, caching, rate limiting
   - Human escalation for sensitive issues
   - Docker Compose + observability

2. **Autonomous Research Assistant** 📚
   - Sequential pipeline: Search → Read → Analyze → Compare → Write
   - Multi-LLM comparison (Anthropic + OpenAI)
   - Web scraping (DuckDuckGo, Wikipedia)
   - PDF and HTML extraction
   - Report generation (Markdown)
   - Example outputs included

3. **Multi-Agent Code Review System** 👨‍💻
   - Parallel: [Style, Security, Logic, Tests] → Collaborative Review
   - Multiple LLMs for consensus (GPT-4, Claude, Gemini)
   - Linter integration (ruff, golangci-lint)
   - Security scanning (bandit, gosec)
   - GitHub integration
   - Human approval workflow

4. **Multi-LLM Cost Optimizer**
   - Route requests to optimal model based on complexity
   - Cost tracking and budget enforcement
   - Quality vs cost tradeoffs
   - A/B testing different models
   - Performance benchmarking

5. **Cross-Language Distributed System**
   - Python and Go agents communicating
   - Multiple transport protocols
   - Distributed tracing across languages
   - Load balancing
   - Health checks and failover

**Each example includes**:
- Complete Docker Compose setup
- Kubernetes manifests (optional)
- Full observability (tracing + metrics)
- Comprehensive tests
- Architecture documentation
- Deployment guides

#### Security Enhancements

**Issue #77: Authentication & Authorization Framework** ✅
- **Authentication**: API key, JWT, OAuth2 support
  - Multiple auth method support
  - Token validation and refresh
  - Session management
- **Authorization**: Role-based access control (RBAC)
  - Role definitions and assignments
  - Permission checking
  - Resource-level access control
- **Middleware**: Easy integration with existing auth systems
- **Examples**: Integration patterns for common auth systems

**Issue #78: TLS Encryption for gRPC** ✅
- **Secure gRPC**: Full TLS support for gRPC transport
  - Server-side TLS configuration
  - Client certificate validation
  - mTLS support (mutual authentication)
- **Certificate Management**: Automated cert loading and validation
- **Production Ready**: Secure by default in production deployments

**Issue #81: Comprehensive Input Validation** ✅
- **Request Validation**: Schema-based validation for all inputs
- **Type Checking**: Runtime type validation
- **Bounds Checking**: Length limits, range validation
- **Sanitization**: Input cleaning and normalization
- **Error Handling**: Clear validation error messages

**Issue #82: Error Message Sanitization** ✅
- **Information Disclosure Prevention**: Sanitize stack traces and internal errors
- **User-Safe Errors**: Clean error messages for external users
- **Debug Mode**: Detailed errors for development, sanitized for production
- **Audit Trail**: Log full errors internally while showing sanitized externally

**Issue #83: Security Middleware as Default** ✅
- **Secure by Default**: Security middleware enabled in production mode
- **Opt-Out**: Explicit opt-out required to disable security
- **Configuration**: Easy security policy configuration
- **Best Practices**: Follow OWASP guidelines by default

**Issue #66: Security Policy & Compatibility Matrix** ✅
- **SECURITY.md**: Vulnerability reporting, supported versions, security best practices
- **Compatibility Matrix**: Python/Go versions, OS support, transport protocols, LLM providers
- **Documentation**: Comprehensive security and compatibility documentation

### Changed

#### Performance Improvements

**Issue #87: Connection Pooling** ✅
- **HTTP Transport**: Connection pooling for HTTP/1.1, HTTP/2, HTTP/3
  - Python: httpx.Limits (100 max connections, 20 keepalive)
  - Go: http.Transport pooling (100 max idle, 20 per host, 90s timeout)
- **gRPC Transport**: Channel pooling and keepalive
  - Python: Channel options (10s keepalive ping, 5min max age)
  - Go: keepalive.ClientParameters (10s ping, 5s timeout)
- **Impact**: 20-35% latency reduction by eliminating 10-50ms connection overhead
- **All Transports**: HTTP, gRPC (both Python and Go)

**Issue #89: Cache Lock Contention Fix** ✅
- **Python**: AsyncRWLock with async read-write coordination
  - Multiple concurrent readers or single writer
  - GIL-free safe (Python 3.13+ compatible)
  - Graceful asyncio task cancellation
- **Go**: sync.RWMutex for efficient concurrent cache reads
- **Impact**: Eliminates lock contention for read-heavy workloads
- **Cache Performance**: Near-instant cache hits with concurrent reads

#### Observability Enhancements

**Prometheus Alerts & SLOs** ✅
- **Alert Rules**: Pre-configured Prometheus alerts for common issues
  - High error rates
  - Slow response times
  - Resource exhaustion
- **SLO Definitions**: Service Level Objectives for production monitoring
  - Latency targets (p50, p95, p99)
  - Error rate thresholds
  - Availability goals
- **Dashboards**: Grafana dashboard templates

**Resource Metrics** ✅
- **CPU Metrics**: Process and system CPU usage
- **Memory Metrics**: Heap size, GC stats, memory limits
- **Runtime Metrics**: Goroutine count, thread count, open file descriptors
- **Python & Go**: Language-specific metrics for both runtimes

### Fixed

**Test Stability** ✅
- **Flaky Tests**: Comprehensive remediation for tests that failed under load
  - Increased timeouts for CI environments
  - Better test isolation
  - Fixed race conditions
- **Pytest Config**: Corrected pytest configuration for proper test discovery
- **Go Examples**: Fixed Go example structure for consistency

**Documentation** ✅
- **Go Distribution**: Added sync documentation and tooling
- **Performance Reviews**: Performance optimization documentation
- **Security Audits**: Comprehensive security documentation and audit trails

### Documentation

- **Security**: Comprehensive security policy and best practices (SECURITY.md)
- **Compatibility**: Python/Go/OS/LLM compatibility matrix (docs-site/compatibility.md)
- **Safety Framework**: Agent safety patterns and implementation (docs/safety.md)
- **Budget Pattern**: Reasoning budget and extended thinking (docs/BUDGET.md)
- **Examples**: 5 complete end-to-end applications with architecture docs
- **Performance**: Monitoring and optimization guides

### Breaking Changes

**None** - This release maintains full backward compatibility with v0.9.0

### Upgrade Guide

No breaking changes. To upgrade from v0.9.0:

```bash
# Python
pip install --upgrade agenkit

# Go
go get -u github.com/scttfrdmn/agenkit/agenkit-go@v0.10.0
```

New features are opt-in:
- Security middleware can be explicitly enabled
- Connection pooling is automatic (no config needed)
- Advanced patterns available via new modules

### What's Next: v1.0.0 (June 2026)

With Phases 7 and 8 complete, v0.10.0 represents the feature-complete state before v1.0.0. The path to v1.0.0 focuses on:

1. **Real-World Validation**: Gathering production feedback
2. **API Stabilization**: Finalizing interfaces based on usage
3. **Additional Patterns**: Issue #64 (Go pattern implementations)
4. **npm Publication**: TypeScript package release
5. **Documentation Polish**: Video tutorials, additional guides

**Timeline**: 6 months of production validation before v1.0.0 stable API guarantee

### Technical Details

- **Code Size**: ~45,000 lines (Python + Go + TypeScript)
- **Test Coverage**: 900+ tests (Python), 250+ tests (Go), 98 tests (TypeScript)
- **Languages**: Python 3.10+, Go 1.21+, TypeScript 5.0+
- **Security**: Zero known vulnerabilities (pip-audit, govulncheck)
- **Performance**: Connection pooling, async locks, optimized caching
- **Production**: Docker, Kubernetes, full observability, security hardened

## [0.9.0] - 2025-11-15

### 🎉 First Public Release - Production Ready, API Stabilizing

**Website:** [https://agenkit.dev](https://agenkit.dev)

This is the first public release of Agenkit. All 5 development phases are complete, and the framework is production-ready with comprehensive testing, security validation, and deployment infrastructure. We're releasing as 0.9.0 to signal that while the implementation is solid, we're seeking real-world feedback to validate and refine the API before committing to 1.0.0 stability.

**Path to 1.0.0:** After gathering user feedback and real-world validation over the next few months, we'll release 1.0.0 with a stable API guarantee.

**Key Highlights:**
- ✅ **Zero Security Vulnerabilities** - Passed Python (pip-audit) and Go (govulncheck) security scans
- ✅ **867 Tests Passing** - Comprehensive test suite with 100% individual test pass rate
- ✅ **Production Infrastructure** - Docker, Kubernetes, full observability ready
- ✅ **Official Website** - Launched at agenkit.dev
- 🔄 **Beta Status** - API stabilizing, seeking real-world feedback before 1.0.0

### Added

#### Phase 2: Transport Layer
- **HTTP Transport**: Full HTTP/1.1, HTTP/2, and HTTP/3 support
- **gRPC Transport**: High-performance binary protocol for microservices
- **WebSocket Transport**: Bidirectional streaming communication
- **Remote Agent Adapters**: Seamless Python ↔ Go cross-language agent communication
- **Protocol Adapters**: Consistent interface across all transport mechanisms
- **Transport Examples**: 3 comprehensive examples for HTTP, gRPC, and WebSocket

#### Phase 3: Middleware & Resilience
- **Circuit Breaker Middleware**: Fail-fast pattern with automatic recovery
- **Retry Middleware**: Exponential backoff with jitter for transient failures
- **Timeout Middleware**: Request deadline enforcement
- **Rate Limiter Middleware**: Token bucket algorithm for request rate control
- **Caching Middleware**: LRU cache with TTL support
- **Batching Middleware**: Request aggregation for improved efficiency
- **Middleware Examples**: 6 practical examples demonstrating each middleware

#### Phase 4: Testing & Quality
- **Comprehensive Test Suite**: 867 tests total, 100% individual test pass rate
- **Cross-Language Integration Tests**: 76 tests validating Python ↔ Go compatibility
  - Agent communication tests
  - Transport layer tests (HTTP, gRPC, WebSocket)
  - Middleware integration tests
  - Observability cross-language tests (W3C Trace Context)
- **Chaos Engineering Tests**: 53 tests for resilience validation
  - Network failure scenarios
  - Service crash recovery
  - Slow response handling
  - Partial failure testing
- **Property-Based Tests**: 37 tests using Hypothesis
  - Message invariants
  - Transport protocol properties
  - Middleware behavior verification
- **Full Observability Integration**:
  - OpenTelemetry distributed tracing with W3C Trace Context propagation
  - Prometheus metrics collection
  - Structured logging with trace correlation
  - TracingMiddleware and MetricsMiddleware
  - Cross-language trace propagation (Python ↔ Go)

#### Phase 5: DevOps & Release
- **Docker Images**:
  - Multi-stage Python image (python:3.11-slim base)
  - Multi-stage Go image (golang:1.21-alpine + alpine:3.19 runtime)
  - Security hardening (non-root user UID 1000, dropped capabilities)
  - Optimized build times with layer caching
- **Docker Compose**:
  - Full observability stack (Jaeger + Prometheus)
  - Python and Go agent services
  - Network isolation and service discovery
- **Kubernetes Deployment**:
  - 9 production-ready manifests
  - Namespace, ConfigMap, Deployments, Services
  - Ingress with TLS support
  - Horizontal Pod Autoscaler (3-10 replicas, CPU/memory-based)
  - Health checks (liveness and readiness probes)
  - Security contexts (non-root, read-only filesystem, no privilege escalation)
  - Resource limits and requests
  - Prometheus scraping annotations
- **Deployment Documentation**:
  - Comprehensive deploy/README.md guide
  - Docker deployment instructions
  - Kubernetes deployment guide
  - Production deployment checklist
  - Monitoring and troubleshooting
  - Security considerations
  - Performance tuning guide

#### Examples & Documentation
- **27+ Comprehensive Examples**: Expanded from 6 to 27+ examples covering:
  - Core patterns (6 examples)
  - Transport layer (3 examples)
  - Middleware (6 examples)
  - Advanced topics (observability, remote agents, streaming)
- **Updated Documentation**:
  - Production-ready README with architecture diagram
  - Complete deployment guide
  - Observability documentation
  - Security best practices
  - Performance benchmarks and baselines

### Changed
- **Go Implementation**: Added full agenkit-go package with feature parity
- **Performance Benchmarks**: Comprehensive baseline measurements
  - Go HTTP: 18.5x faster than Python (0.055ms vs 1.02ms)
  - HTTP/3: 21% faster for concurrent workloads
  - Middleware overhead: <0.01% of total request time
  - Transport overhead: <1% in realistic LLM workloads
- **Test Coverage**: Increased from 36 tests to 867 tests (100% individual test pass rate)
- **Project Structure**: Organized into phases with clear separation of concerns

### Performance
- **Transport Layer**:
  - Go HTTP: 0.055ms per request
  - Python HTTP: 1.02ms per request
  - Message scaling: 10,000x size = 190x latency (excellent efficiency)
- **Middleware Overhead**:
  - Circuit Breaker: 14.6µs (Python), 10.0µs (Go)
  - Retry: 0.9µs (Python), 0.8µs (Go)
  - Timeout: 2.1µs (Python), 1.5µs (Go)
  - Rate Limiter: 4.0µs (Python), 2.5µs (Go)

### Technical Details
- **Code Size**: ~35,000 lines (Python + Go)
- **Languages**: Python 3.10+, Go 1.21+
- **Container Support**: Docker images and Kubernetes manifests
- **Observability**: OpenTelemetry tracing + Prometheus metrics
- **Security**: Non-root containers, dropped capabilities, TLS support
- **Scalability**: Kubernetes HPA with 3-10 replica autoscaling

## [0.1.0] - 2024-01-08

### Added
- Core interfaces: `Agent`, `Tool`, `Message`, `ToolResult`
- Core orchestration patterns: `SequentialPattern`, `ParallelPattern`, `RouterPattern`
- Comprehensive test suite (36 unit tests, 100% passing)
- Performance benchmarks proving <15% interface overhead
- Type checking with mypy strict mode (zero errors)
- Complete API documentation with examples
- Six practical examples demonstrating all features:
  - Basic agent creation
  - Sequential pattern (pipeline)
  - Parallel pattern (concurrent processing)
  - Router pattern (conditional dispatch)
  - Tool usage
  - Pattern composition
- Project structure with modern Python packaging
- Performance optimization (attribute caching, fast-path optimizations)

### Technical Details
- ~500 lines of production-quality code
- Async-first design using modern Python standards
- Immutable data structures (frozen dataclasses)
- Metadata extension points everywhere
- Full type hints with mypy strict compliance
- Zero technical debt

### Performance
- Agent interface overhead: ~2-3%
- Tool interface overhead: ~3-7%
- Sequential pattern overhead: ~3-8%
- Parallel pattern overhead: ~2-4%
- Router pattern overhead: ~8-12%
- Production impact: <0.001% (microsecond-level overhead vs LLM calls)

[unreleased]: https://github.com/agenkit/agenkit/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/agenkit/agenkit/releases/tag/v0.9.0
[0.1.0]: https://github.com/agenkit/agenkit/releases/tag/v0.1.0
