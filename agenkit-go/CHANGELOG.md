# Changelog

All notable changes to the agenkit project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
