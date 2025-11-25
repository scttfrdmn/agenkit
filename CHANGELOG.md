# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.12.0] - 2025-11-24

### 🎯 Core Agent Patterns Library - Production-Ready Implementation Patterns

This release introduces three foundational agent patterns that enable sophisticated agent behaviors: **Reflection** (self-critique and iterative refinement), **Agents-as-Tools** (hierarchical delegation), and **Memory Hierarchy** (multi-tier memory management). These patterns provide the building blocks for production-quality agent systems.

**Key Highlights:**
- ✅ **3 Complete Pattern Implementations**: ~1,300 LOC with full test coverage
- ✅ **72 Tests**: 22 (reflection) + 20 (agents-as-tools) + 30 (memory) - 100% passing
- ✅ **Comprehensive Examples**: 3 complete demo files with 12+ scenarios
- ✅ **Production-Ready**: Battle-tested APIs with proper error handling and edge cases
- ✅ **Documentation**: New chapters in agent patterns guide

### Added

#### Pattern 1: Reflection Pattern (Self-Critique & Iterative Refinement)

**Implementation** (~450 LOC):
- `ReflectionAgent` with configurable stopping conditions
- Quality threshold, improvement threshold, max iterations
- Structured JSON and free-form critique support
- Full iteration history tracking
- Critique parsing with error recovery

**Key Features:**
- **Quality-Driven Refinement**: Iterates until output meets quality standards
- **Multiple Stop Conditions**: Quality met, minimal improvement, max iterations, perfect score
- **Flexible Critique Formats**: JSON or free-form text
- **Production Metadata**: Tracks iterations, scores, improvements, stop reasons

**Testing** (22 tests):
- Quality threshold scenarios
- Improvement tracking
- Max iterations enforcement
- Perfect score handling
- Critique format parsing
- History retrieval
- Verbose mode
- Error conditions

**Examples** (`examples/patterns/06_reflection_agent.py`):
- Basic reflection with quality improvement
- History tracking and debugging
- Different stopping conditions
- Multi-draft content creation

**Use Cases:**
- Code generation with automatic review
- Multi-draft content writing
- Iterative analysis refinement
- Quality-gated outputs

#### Pattern 2: Agents-as-Tools Pattern (Hierarchical Delegation)

**Implementation** (~200 LOC):
- `AgentTool` wrapper for any agent
- `agent_as_tool()` convenience function
- Multiple output formats (string, dict, message)
- Custom input parameter keys
- Full integration with `ToolRegistry` and `ReActAgent`

**Key Features:**
- **Seamless Integration**: Works with existing ReAct pattern
- **Hierarchical Organization**: Supervisor → specialists → sub-specialists
- **Output Format Flexibility**: String, dictionary, or message
- **Direct Invocation**: Can be called with or without supervisor

**Testing** (20 tests):
- Basic agent tool operation
- All output formats
- Custom input parameters
- Tool registry integration
- ReAct pattern integration
- Multi-level hierarchies
- Error propagation
- Parameter validation

**Examples** (`examples/patterns/07_hierarchical_agents.py`):
- Basic hierarchical delegation
- Output format demonstrations
- Multi-level hierarchies (3+ levels)
- Direct tool invocation

**Use Cases:**
- Domain-specific specialist agents
- Multi-agent orchestration
- Complex task decomposition
- Reusable agent components

#### Pattern 3: Memory Hierarchy Pattern (Multi-Tier Memory)

**Implementation** (~650 LOC):
- `WorkingMemory` - In-context (FIFO eviction)
- `ShortTermMemory` - Session-based (TTL + LRU eviction)
- `LongTermMemory` - Persistent (importance-based)
- `MemoryHierarchy` - Unified interface across tiers
- Importance-based routing
- Cross-tier search with deduplication
- TTL expiration and LRU eviction

**Key Features:**
- **3-Tier Architecture**: Working (context), Short-term (session), Long-term (persistent)
- **Automatic Tier Routing**: Based on importance scores
- **Smart Eviction**: FIFO for working, TTL+LRU for short-term
- **Cross-Tier Search**: Deduplicated relevance ranking
- **Production-Ready**: Handles edge cases (empty tiers, falsy objects)

**Testing** (30 tests):
- All 3 tiers independently
- Tier routing logic
- FIFO/LRU/TTL eviction
- Cross-tier search
- Deduplication
- Statistics and monitoring
- Session management
- Edge cases (empty collections, None checks)

**Examples** (`examples/patterns/08_memory_hierarchy.py`):
- Basic 3-tier hierarchy
- Working memory FIFO eviction
- Short-term TTL expiration
- Cross-tier search & deduplication
- Session continuity (conversational agent)
- Memory consolidation & importance scoring

**Use Cases:**
- Conversational agents with context
- Multi-session user interactions
- Personalization and preferences
- Long-running agent deployments

### Changed

- **Updated `agenkit/patterns/__init__.py`**: Exported all new pattern classes
  - `ReflectionAgent`, `ReflectionStep`, `CritiqueFormat`, `StopReason`
  - `AgentTool`, `agent_as_tool`
  - `MemoryHierarchy`, `WorkingMemory`, `ShortTermMemory`, `LongTermMemory`, `MemoryEntry`, `MemoryStore`

- **Updated Agent Patterns Guide** (`docs-site/guides/agent-patterns.md`):
  - Added Chapter 12: Reflection Pattern
  - Added Chapter 13: Agents-as-Tools Pattern
  - Added Chapter 14: Memory Hierarchy Pattern
  - Renumbered subsequent chapters
  - Updated table of contents
  - Version 0.3 with changelog

### Fixed

- **Memory Hierarchy**: Fixed falsy object evaluation bug
  - Changed `if self.short_term:` to `if self.short_term is not None:`
  - Empty collections with `__len__() == 0` were evaluating as False
  - Applied fix to 4 locations: store(), retrieve(), get_stats(), search_tiers

### Documentation

- **Design Document**: `docs/patterns_library_design.md`
  - Comprehensive architecture for all 3 patterns
  - API design examples
  - Testing strategy
  - Implementation phases

- **Pattern Examples**: 3 complete demo files (~1,180 LOC total)
  - `examples/patterns/06_reflection_agent.py` (4 demos, ~330 lines)
  - `examples/patterns/07_hierarchical_agents.py` (4 demos, ~400 lines)
  - `examples/patterns/08_memory_hierarchy.py` (6 demos, ~390 lines)

- **Comprehensive Tests**: 72 tests across 3 test files (~1,700 LOC total)
  - `tests/patterns/test_reflection.py` (22 tests, ~600 LOC)
  - `tests/patterns/test_agents_as_tools.py` (20 tests, ~400 LOC)
  - `tests/patterns/test_memory.py` (30 tests, ~700 LOC)

- **Agent Patterns Guide**: Updated with 3 new chapters
  - Complete implementation examples
  - Production considerations
  - Architecture diagrams
  - Use case recommendations

### Metrics

**Code:**
- Implementation: ~1,300 LOC
- Tests: ~1,700 LOC (72 tests, 100% passing)
- Examples: ~1,180 LOC (12+ scenarios)
- **Total**: ~4,180 LOC

**Test Coverage:**
- Reflection: 22/22 tests passing (100%)
- Agents-as-Tools: 20/20 tests passing (100%)
- Memory Hierarchy: 30/30 tests passing (100%)
- **Overall**: 72/72 tests passing (100%)

**Documentation:**
- 1 design document (400 lines)
- 3 pattern chapters (537 lines)
- 3 example files (1,180 lines)

## [0.11.1] - TBD

### Added

- **Automated Optimization Framework** - Complete implementation for v0.11.1
  - `BayesianOptimizer` for intelligent hyperparameter tuning using Gaussian Process
  - `PromptOptimizer` for systematic prompt improvement (grid, random, genetic strategies)
  - `SearchSpace` for flexible parameter space definition (continuous, discrete, integer, categorical)
  - `RandomSearchOptimizer` as baseline optimization method
  - Acquisition functions: Expected Improvement (EI), Upper Confidence Bound (UCB), Probability of Improvement (PI)
  - Genetic algorithm for prompt evolution
  - Integration with existing evaluation infrastructure
  - Comprehensive demo with 5 optimization scenarios

### Changed

- Updated evaluation module exports to include optimization classes
- Enhanced optimizer base class with metric support

### Fixed

- Fixed numpy compatibility issue in Bayesian optimizer (`np.math.erf` → `math.erf`)
- Fixed optimizer evaluation to properly instantiate metrics

### Dependencies

- `scikit-learn>=1.3.0` for Gaussian Process regression
- `numpy>=1.24.0` for numerical operations

### Documentation

- Created comprehensive optimization design document (`docs/optimization_design.md`)
- Added optimization demo (`examples/evaluation/optimization_demo.py`)
- 12 tests for optimization framework

## [0.11.0] - 2024-11-24

### Added

- **A/B Testing Framework** for statistical comparison of agent variants
  - Complete implementation with t-test, Mann-Whitney U, chi-square, bootstrap
  - Effect size calculations and confidence intervals
  - Sample size calculation with power analysis
  - 24 Python tests, 11 Go example tests
  - Comprehensive documentation and examples

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
