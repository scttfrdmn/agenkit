# Changelog

All notable changes to the agenkit project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.15.0] - 2025-11-25

### Added

- **🎉 Go Achieves 100% Pattern Parity!** - All 8 remaining patterns implemented:

  - **Orchestration Pattern** (`patterns/orchestration.go`)
    - Sequential orchestration with ordered execution
    - Parallel orchestration with concurrent execution
    - Router orchestration with conditional routing
    - Comprehensive error handling and context support

  - **ReAct Pattern** (`patterns/react.go`, 360 LOC, 21 tests)
    - Reasoning-Acting cycle with interleaved thought and action
    - Tool integration during reasoning process
    - Observation loop for continuous improvement
    - Configurable max steps and verbose mode

  - **Conversational Pattern** (`patterns/conversational.go`, 254 LOC, 20 tests)
    - Multi-turn dialogue management
    - Context retention across conversations
    - Message history with configurable limits
    - Session-based conversation tracking

  - **Task Pattern** (`patterns/task.go`, 244 LOC, 18 tests)
    - Task-oriented workflow execution
    - Timeout handling with configurable durations
    - Retry logic with exponential backoff
    - Task status tracking and result management

  - **Multiagent Pattern** (`patterns/multiagent.go`, 332 LOC, 21 tests)
    - Orchestrator coordination for agent collaboration
    - Consensus mechanisms for decision-making
    - Agent capability matching and routing
    - Parallel and sequential execution modes

  - **Planning Pattern** (`patterns/planning.go`, 458 LOC, 30 tests)
    - Step-based plan generation and execution
    - Parallel and sequential plan execution
    - Dependency management between steps
    - Progress tracking with completion status
    - Plan validation and error handling

  - **Autonomous Pattern** (`patterns/autonomous.go`, 308 LOC, 20 tests)
    - Goal-based autonomous agents with self-direction
    - Priority-based goal selection
    - Multiple stop conditions (max iterations, manual stop, custom)
    - Worker function pattern for customization
    - Goal status transitions (active → completed → abandoned)

  - **Memory Hierarchy Pattern** (`patterns/memory.go`, 542 LOC, 29 tests)
    - Three-tier memory architecture (Working, ShortTerm, LongTerm)
    - Working Memory: FIFO eviction, in-context storage
    - ShortTerm Memory: TTL-based expiration, LRU eviction
    - LongTerm Memory: Importance-based retention, keyword matching
    - Thread-safe operations with mutex protection
    - Cross-tier retrieval with deduplication

  - **Reasoning with Tools Pattern** (`patterns/reasoning_with_tools.go`, 531 LOC, 30 tests)
    - Interleaved reasoning: Think ↔ Act (vs ReAct's sequential Think → Act)
    - Tools available DURING reasoning, not just after
    - Text-based tool call protocol ("TOOL_CALL:", "PARAMETERS:")
    - Conclusion detection with multiple markers
    - ReasoningTrace for complete step tracking
    - Context accumulation across iterations

### Testing

- Added 188 new tests across 8 patterns
- Total pattern tests: 276 (100% pass rate)
- Comprehensive coverage including:
  - Constructor and configuration validation
  - Core functionality and edge cases
  - Error handling and context cancellation
  - Integration scenarios
  - Performance characteristics

### Milestone

🎉 **Go reaches 100% pattern parity with Python and TypeScript!**

**Achievement Summary:**
- **11/11 patterns** implemented (100% parity)
- **~4,700 total LOC** across all patterns
- **276 comprehensive tests** (100% pass rate)
- **5 months ahead of roadmap schedule** (target was April 2026)

**Three-Language Parity Status:**
| Language | Patterns | Tests | Status |
|----------|----------|-------|--------|
| Python | 11/11 | ~300 | ✅ Reference |
| TypeScript | 11/11 | 514 | ✅ Complete |
| Go | 11/11 | 276 | ✅ **COMPLETE** |

This represents a major acceleration of the 6-language roadmap, with 3 languages now at full parity!

## [0.14.0] - 2025-11-24

### Added

- **Go Critical Patterns** - 3 essential patterns for advanced agent orchestration:
  - **Reflection Pattern** (`patterns/reflection.go`, 467 LOC)
    - Generator-critic coordination for iterative refinement
    - Multiple stop conditions (quality threshold, max iterations, improvement threshold)
    - Support for structured (JSON) and free-form critique parsing
    - Comprehensive metadata tracking with reflection history
    - Context cancellation support
    - 14 comprehensive tests, working example
  - **Agents-as-Tools Pattern** (`patterns/agents_as_tools.go`, 297 LOC)
    - Hierarchical agent delegation (supervisor → specialists)
    - Multiple output formats (string, dict, message)
    - Configurable input parameters and metadata
    - `AgentAsTool` and `AgentAsToolSimple` convenience functions
    - Full observability with metadata tracking
    - 17 comprehensive tests, working example
  - **Bayesian Optimization** (`evaluation/bayesian_optimizer.go`, 491 LOC)
    - Search space with 4 parameter types (continuous, integer, discrete, categorical)
    - 3 acquisition functions (Expected Improvement, UCB, Probability of Improvement)
    - Simplified surrogate model using local statistics
    - Comprehensive result tracking and analysis
    - Support for both maximization and minimization
    - 18 comprehensive tests, working example

- **Examples**:
  - `examples/patterns/reflection_example.go` - Iterative code refinement demo
  - `examples/patterns/agents_as_tools_example.go` - Supervisor-specialist delegation demo
  - `examples/evaluation/bayesian_optimization_example.go` - Hyperparameter tuning demo

### Changed

- Organized evaluation examples into `examples/evaluation/` directory
- Enhanced patterns module with critical orchestration patterns

### Fixed

- Fixed `configSimilarity` in Bayesian Optimizer to use floating-point arithmetic for accurate similarity calculation
- Fixed mock response count mismatch in Reflection pattern tests

### Testing

- Added 49 new tests for Go patterns and evaluation
  - Reflection: 14 tests
  - Agents-as-Tools: 17 tests
  - Bayesian Optimization: 18 tests
- All 113 tests passing in patterns and evaluation modules

### Documentation

- Comprehensive inline documentation for all new patterns
- Example code demonstrating practical usage scenarios
- References to academic papers (Reflexion, Self-Refine)

### Milestone

🎉 **Go reaches 70% parity with Python** - Critical patterns implemented

## [0.11.0] - TBD

### Added

- **A/B Testing Framework** for statistical comparison of agent variants
  - `ABTest` class for orchestrating A/B experiments
  - `ABVariant` for representing control and treatment variants
  - `ABResult` with comprehensive statistical analysis
  - Support for multiple statistical tests:
    - Independent samples t-test (parametric)
    - Mann-Whitney U test (non-parametric)
    - Chi-square test (categorical)
    - Bootstrap methods (distribution-free)
  - Effect size calculations (Cohen's d, rank-biserial correlation)
  - Confidence interval computation for all test types
  - `calculate_sample_size()` function for power analysis
  - `SignificanceLevel` enum (P_0_001, P_0_01, P_0_05, P_0_10)
  - `StatisticalTestType` enum for test selection
  - Complete Go implementation with feature parity
  - Comprehensive demo with 5 scenarios (`examples/evaluation/ab_testing_demo.py`)
  - 24 Python tests for A/B testing framework
  - 11 Go example tests

### Changed

- Updated evaluation module exports to include A/B testing classes
- Enhanced `conftest.py` with proper timeouts for async cleanup

### Fixed

- Fixed pytest hanging issue by adding timeouts to async resource cleanup
- Fixed deprecated `datetime.utcnow()` usage (replaced with `datetime.now(timezone.utc)`)
- Resolved Go duplicate function declarations in evaluation package
- Updated Go example test expected outputs for accuracy

### Dependencies

- **Python**: Added `scipy>=1.11.0` for statistical functions
- **Go**: Added `gonum.org/v1/gonum v0.16.0` for statistical functions

### Documentation

- Created comprehensive A/B Testing Guide (`docs/ab_testing_guide.md`)
- Created release notes (`RELEASE_NOTES_v0.11.0.md`)
- Added inline documentation for all A/B testing classes and functions

## [0.10.1] - 2024-11-24

### Fixed

- Fixed 50 errcheck issues in Go codebase using idiomatic error handling patterns
- Added proper `defer func() { _ = x.Close() }()` for cleanup operations

## [0.10.0] - 2024-11-24

### Added

- **Phase 7: Observability & Instrumentation**
  - OpenTelemetry integration for distributed tracing
  - Prometheus metrics with custom exporters
  - Health check endpoints
  - Context propagation across service boundaries
  - W3C Trace Context format support
  - Resource metrics collection (CPU, memory, runtime stats)

- **Phase 8: Performance Optimization**
  - HTTP/2 and HTTP/3 (QUIC) transport support
  - Connection pooling for HTTP and gRPC transports
  - Read-write locks for cache middleware to reduce contention
  - Prometheus alert rules and SLO definitions
  - Performance benchmarks

### Changed

- Enhanced middleware stack with tracing support
- Improved transport layer with connection reuse

### Fixed

- Cache lock contention issues with read-write locks
- Memory leaks in connection handling

### Documentation

- Added observability setup guide
- Performance tuning recommendations
- SLO and alerting documentation

## [0.9.0] - 2024-11-10

### Added

- **Evaluation Framework** (Phases 1-8, excluding A/B testing)
  - Core evaluation infrastructure (`Evaluator`, `Metric`, `EvaluationResult`)
  - Session recording and replay (`SessionRecorder`, `SessionReplay`)
  - Regression detection (`RegressionDetector`)
  - Context tracking (`ContextMetrics`, `CompressionMetrics`)
  - Quality metrics (`AccuracyMetric`, `PrecisionRecallMetric`, `QualityMetrics`)
  - Latency tracking (`LatencyMetric`)
  - Benchmark suites (`Benchmark`, `BenchmarkSuite`)

### Changed

- Improved error handling across evaluation modules
- Enhanced type safety with stricter mypy checks

## Earlier Versions

See git history for changes in versions prior to 0.9.0.

---

[0.14.0]: https://github.com/scttfrdmn/agenkit/compare/v0.10.1...v0.14.0
[0.11.0]: https://github.com/scttfrdmn/agenkit/compare/v0.10.1...v0.11.0
[0.10.1]: https://github.com/scttfrdmn/agenkit/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/scttfrdmn/agenkit/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/scttfrdmn/agenkit/releases/tag/v0.9.0
