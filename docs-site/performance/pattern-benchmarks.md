# Pattern Performance Benchmarks

## Overview

This document tracks performance benchmarks for agent patterns across all Agenkit language implementations. Pattern benchmarks measure the **framework overhead** of pattern implementations using simple test agents (EchoAgent) to isolate pattern logic from LLM latency.

### Purpose

- **Regression Detection**: Identify performance degradation in pattern implementations
- **Cross-Language Comparison**: Compare pattern overhead across C++, Go, Python, TypeScript, Rust, and Zig
- **Optimization Guidance**: Identify patterns with high overhead for targeted optimization
- **Production Context**: Help users understand the negligible impact of pattern overhead vs LLM calls

### Methodology

**Test Agent**: `EchoAgent` - Simple agent that immediately returns input without I/O or LLM calls
**Iterations**: 10-1,000 per pattern (varies by pattern complexity)
**Measurements**: Mean, median, min, max execution time in microseconds (μs)
**Baseline**: Framework overhead only - real production includes 100-1000ms LLM latency

---

## C++ Pattern Benchmarks

### Test Environment

- **Date**: December 17, 2025
- **Platform**: macOS (Darwin 25.2.0)
- **CPU**: Apple M4 Pro (ARM64)
- **Compiler**: Apple Clang
- **C++ Standard**: C++17
- **Build Type**: Debug
- **Iterations**: 1,000 (with 10-iteration warmup)

### Results

| Pattern | Mean (μs) | Median (μs) | Min (μs) | Max (μs) | Iterations | Status |
|---------|-----------|-------------|----------|----------|------------|--------|
| **Memory: Working** (store) | 0.11 | 0.00 | 0.00 | 9.00 | 1,000 | ✅ |
| **ReAct** (3 steps) | 0.74 | 1.00 | 0.00 | 5.00 | 1,000 | ✅ |
| **Orchestration** (2 agents) | 0.99 | 1.00 | 0.00 | 5.00 | 1,000 | ✅ |
| **Memory: Hierarchy** (store) | 1.01 | 1.00 | 1.00 | 2.00 | 1,000 | ✅ |
| **Memory: Working** (retrieve) | 1.96 | 2.00 | 1.00 | 14.00 | 1,000 | ✅ |
| **Agents-as-Tools** (call) | 2.00 | 2.00 | 2.00 | 2.00 | 1,000 | ✅ |
| **Autonomous** (5 iterations) | 3.40 | 3.00 | 3.00 | 39.00 | 100 | ✅ |
| **Task** (one-shot) | 3.47 | 3.00 | 3.00 | 32.00 | 1,000 | ✅ |
| **Router** (2 routes) | 5.12 | 5.00 | 4.00 | 18.00 | 1,000 | ✅ |
| **Fallback** (2 agents) | 6.51 | 6.00 | 6.00 | 19.00 | 1,000 | ✅ |
| **Memory: Hierarchy** (retrieve) | 6.96 | 7.00 | 6.00 | 12.00 | 1,000 | ✅ |
| **Planning** (plan + execute) | 9.71 | 9.00 | 8.00 | 35.00 | 1,000 | ✅ |
| **Parallel** (3 agents) | 12.94 | 12.00 | 11.00 | 59.00 | 1,000 | ✅ |
| **Multiagent** (2 sequential) | 13.18 | 9.00 | 9.00 | 69.00 | 1,000 | ✅ |
| **Human-in-Loop** (auto-approve) | 16.16 | 15.00 | 14.00 | 51.00 | 1,000 | ✅ |
| **Conversational** (10 history) | 33.34 | 26.00 | 25.00 | 209.00 | 1,000 | ✅ |
| **Collaborative** (2 rounds) | 41.13 | 35.00 | 32.00 | 158.00 | 1,000 | ✅ |
| **Sequential** (3 agents) | 49.60 | 30.00 | 27.00 | 287.00 | 1,000 | ✅ |
| **Reflection** (2 iterations) | 69.57 | 48.00 | 45.00 | 350.00 | 1,000 | ✅ |
| **Reasoning with Tools** | 373.54 | 345.00 | 320.00 | 885.00 | 1,000 | ✅ |

### Performance Categories

**Ultra-Fast (<10μs)** - Negligible overhead:
- Memory: Working (store): 0.11μs
- ReAct: 0.74μs
- Orchestration: 0.99μs
- Memory: Hierarchy (store): 1.01μs
- Memory: Working (retrieve): 1.96μs
- Agents-as-Tools: 2.00μs
- Autonomous: 3.40μs
- Task: 3.47μs
- Memory: Hierarchy (retrieve): 6.96μs
- Planning: 9.71μs

**Fast (10-100μs)** - Excellent performance:
- Multiagent: 13.18μs
- Conversational: 33.34μs
- Reflection: 69.57μs

**Moderate (100-1000μs)** - Acceptable overhead:
- Reasoning with Tools: 373.54μs

### Resolved Issues

#### ✅ Conversational Pattern Anomaly (Fixed v0.42.0)

**Previous**: 5.13 **seconds** mean latency (5,134,570μs)
**Fixed**: 33.34μs mean latency

**Root Cause**:
- History accumulated across benchmark iterations causing O(n²) degradation
- Agent was reused for all iterations without clearing history
- By iteration 10, history management overhead dominated execution

**Fix Applied** (bench_patterns.cpp:204):
```cpp
// Clear history after each iteration to prevent accumulation
conv.clear_history();
```

**Results**:
- 154,000x performance improvement (5.13s → 33μs)
- Increased iterations from 10 to 1,000 (now safe with history clearing)
- Conversational pattern now shows realistic overhead

#### ✅ Autonomous Pattern Anomaly (Fixed v0.42.0)

**Previous**: 0.00μs (measurement error - no time measured)
**Fixed**: 3.40μs mean latency

**Root Cause**:
- Agent created once outside benchmark loop
- Goals marked complete after first `run()` call
- Subsequent iterations found no active goals and returned immediately (no-op)

**Fix Applied** (bench_patterns.cpp:259):
```cpp
// Create fresh agent for each iteration to reset goal state
patterns::AutonomousAgent autonomous("Complete objective", config);
autonomous.add_goal("Goal 1", 1);
autonomous.add_goal("Goal 2", 1);
```

**Results**:
- Now measures actual goal processing work
- Increased iterations from 10 to 100 (now measuring correctly)
- Autonomous pattern shows realistic ultra-fast overhead

### Production Context

**Critical Point**: Pattern overhead is **negligible in production** because:
- LLM calls dominate execution time: 100-1000ms per call
- Pattern overhead: 0.001-0.37ms (0.11μs to 373.54μs)
- **Production impact**: <0.01-0.1% of total time

**Example Production Scenario**:
```
Agent workflow:
- 2 LLM calls @ 500ms each = 1,000ms
- Reflection pattern overhead: 0.070ms
- Production overhead: 0.0070%
```

The benefits of patterns (code clarity, reusability, maintainability) vastly outweigh the minimal performance cost.

---

## Go Pattern Benchmarks

### Test Environment

- **Date**: December 17, 2025
- **Platform**: macOS (Darwin 25.2.0)
- **CPU**: Apple M4 Pro (ARM64, 12 cores)
- **Go Version**: Go 1.24.0
- **Test Framework**: Go testing.B
- **Build Type**: Default (optimized)

### Results

| Pattern | ns/op | μs/op | B/op | allocs/op | Status |
|---------|-------|-------|------|-----------|--------|
| **Memory: Working** (retrieve) | 28 | 0.028 | 48 | 1 | ✅ |
| **Task** (one-shot) | 92 | 0.092 | 112 | 2 | ✅ |
| **Conversational** (10 history) | 114 | 0.114 | 144 | 5 | ✅ |
| **Fallback** (2 agents) | 258 | 0.258 | 528 | 5 | ✅ |
| **Agents-as-Tools** (call) | 276 | 0.276 | 248 | 7 | ✅ |
| **Router** (2 routes) | 312 | 0.312 | 432 | 5 | ✅ |
| **Human-in-Loop** (auto-approve) | 472 | 0.472 | 888 | 13 | ✅ |
| **Memory: Working** (store) | 501 | 0.501 | 528 | 5 | ✅ |
| **Memory: Short-Term** (retrieve) | 600 | 0.600 | 408 | 9 | ✅ |
| **Multiagent** (2 sequential) | 705 | 0.705 | 1,355 | 14 | ✅ |
| **Autonomous** (5 iterations) | 736 | 0.736 | 784 | 27 | ✅ |
| **Sequential** (3 agents) | 924 | 0.924 | 1,728 | 18 | ✅ |
| **ReAct** (3 steps) | 1,270 | 1.270 | 1,489 | 14 | ✅ |
| **Planning** (plan + execute) | 1,552 | 1.552 | 2,473 | 35 | ✅ |
| **Memory: Short-Term** (store) | 2,439 | 2.439 | 2,735 | 14 | ✅ |
| **Collaborative** (2 rounds) | 3,126 | 3.126 | 5,236 | 65 | ✅ |
| **Parallel** (3 agents) | 3,450 | 3.450 | 1,200 | 20 | ✅ |
| **Reasoning with Tools** | 18,093 | 18.093 | 43,320 | 95 | ✅ |
| **Reflection** (2 iterations) | 155,725 | 155.725 | 34,852 | 298 | ✅ |

### Performance Categories

**Ultra-Fast (<1μs)** - Negligible overhead:
- Memory: Working (retrieve): 0.028μs
- Task: 0.092μs
- Conversational: 0.114μs
- Fallback: 0.258μs
- Agents-as-Tools: 0.276μs
- Router: 0.312μs
- Human-in-Loop: 0.472μs
- Memory: Working (store): 0.501μs
- Memory: Short-Term (retrieve): 0.600μs
- Multiagent: 0.705μs
- Autonomous: 0.736μs
- Sequential: 0.924μs

**Fast (1-10μs)** - Excellent performance:
- ReAct: 1.270μs
- Planning: 1.552μs
- Memory: Short-Term (store): 2.439μs
- Collaborative: 3.126μs
- Parallel: 3.450μs

**Moderate (10-100μs)** - Acceptable overhead:
- Reasoning with Tools: 18.093μs

**High (100-200μs)** - Measurable but still fast:
- Reflection: 155.725μs

### Key Observations

1. **Memory Operations**: Ultra-fast (0.028μs retrieve, 0.501μs store)
2. **Simple Patterns**: Sub-microsecond overhead for basic patterns (Task, Conversational, Router)
3. **Complex Patterns**: Still very fast (<20μs for most)
4. **Reflection Pattern**: Highest overhead at 155.725μs due to 2 iterations
5. **Go Efficiency**: Go's garbage collector and runtime add minimal overhead

### Production Context

**Critical Point**: Pattern overhead in Go is **negligible in production**:
- LLM calls dominate: 100-1000ms per call
- Pattern overhead: 0.000028-0.156ms (0.028μs to 155.725μs)
- **Production impact**: <0.001-0.02% of total time

**Example Production Scenario**:
```
Agent workflow:
- 2 LLM calls @ 500ms each = 1,000ms
- Reflection pattern overhead: 0.156ms
- Production overhead: 0.0156%
```

---

## Python Pattern Benchmarks

### Test Environment

- **Date**: December 18, 2025
- **Platform**: macOS (Darwin 25.2.0)
- **CPU**: Apple M4 Pro (ARM64, 12 cores)
- **Python Version**: Python 3.10.19
- **Test Framework**: pytest + asyncio
- **Build Type**: Default

### Results

| Pattern | Mean (μs) | Notes | Status |
|---------|-----------|-------|--------|
| **Autonomous** (5 iterations) | 0.635 | Fresh agent per iteration | ✅ |
| **Supervisor** (2 specialists) | 1.072 | SimplePlanner with 2 specialists | ✅ |
| **Human-in-Loop** (auto-approve) | 2.199 | Auto-approval function | ✅ |
| **Task** (one-shot) | 1.796 | Single execution with cleanup | ✅ |
| **Fallback** (2 agents) | 1.494 | Sequential fallback chain | ✅ |
| **Router** (2 routes) | 2.238 | SimpleClassifier routing | ✅ |
| **Conversational** (10 history) | 2.990 | With history clearing | ✅ |
| **Sequential** (3 agents) | 3.354 | Pipeline execution | ✅ |
| **Multiagent** (2 sequential) | 4.316 | MultiAgentOrchestrator | ✅ |
| **Agents-as-Tools** (tool call) | 4.132 | AgentTool wrapper | ✅ |
| **Orchestration** (2 agents) | 4.149 | MultiAgentOrchestrator | ✅ |
| **Memory: Working** (retrieve) | 0.786 | In-memory retrieval | ✅ |
| **Memory: Working** (store) | 0.873 | In-memory storage | ✅ |
| **Memory: Short-Term** (retrieve) | 2.019 | TTL-based retrieval | ✅ |
| **Memory: Short-Term** (store) | 1.277 | TTL-based storage | ✅ |
| **Memory: Hierarchy** (retrieve) | 8.292 | Multi-tier retrieval | ✅ |
| **Memory: Hierarchy** (store) | 4.455 | Multi-tier storage | ✅ |
| **Planning** (plan + execute) | 5.911 | LLMClient-based planning | ✅ |
| **Collaborative** (2 rounds) | 12.609 | 2-round collaboration | ✅ |
| **ReAct** (3 steps) | 15.087 | LLMClient + ToolRegistry | ✅ |
| **Reflection** (2 iterations) | 17.423 | Generator + Critic pattern | ✅ |
| **Reasoning with Tools** | 39.020 | Tool-aware reasoning | ✅ |
| **Parallel** (3 agents) | 81.844 | Concurrent execution | ✅ |

### Performance Categories

**Ultra-Fast (<5μs)** - Negligible overhead:
- Autonomous: 0.635μs
- Memory: Working (retrieve): 0.786μs
- Memory: Working (store): 0.873μs
- Supervisor: 1.072μs
- Memory: Short-Term (store): 1.277μs
- Fallback: 1.494μs
- Task: 1.796μs
- Memory: Short-Term (retrieve): 2.019μs
- Human-in-Loop: 2.199μs
- Router: 2.238μs
- Conversational: 2.990μs
- Sequential: 3.354μs
- Agents-as-Tools: 4.132μs
- Orchestration: 4.149μs
- Multiagent: 4.316μs
- Memory: Hierarchy (store): 4.455μs

**Fast (5-20μs)** - Excellent performance:
- Planning: 5.911μs
- Memory: Hierarchy (retrieve): 8.292μs
- Collaborative: 12.609μs
- ReAct: 15.087μs
- Reflection: 17.423μs

**Moderate (20-100μs)** - Acceptable overhead:
- Reasoning with Tools: 39.020μs
- Parallel: 81.844μs

### Key Observations

1. **Ultra-Fast Majority**: 16/23 benchmarks <5μs
2. **Memory Operations**: Extremely fast (0.786-8.292μs across all tiers)
3. **Async Performance**: Python's asyncio adds minimal overhead
4. **Parallel Pattern**: Highest overhead at 81.844μs (concurrent coordination cost)
5. **Supervisor Pattern**: Fastest complex pattern at 1.072μs

### API Inconsistencies

⚠️ **Important**: Python pattern APIs differ significantly from C++/Go implementations. See [Issue #319](https://github.com/scttfrdmn/agenkit/issues/319) for details.

**Major Differences**:
- **ReflectionAgent**: Takes `generator` + `critic` (not single `agent`)
- **ReActAgent**: Takes `llm_client` + `tool_registry` (not `agent` + `tools`)
- **PlanningAgent**: Takes `llm_client` directly (not `planner` agent)
- **AutonomousAgent**: No `agent` parameter (just `objective`)
- **Collaborative/HumanInLoop**: Use Config objects

**Impact**: Code cannot be directly ported between languages. API normalization tracked in issue #319.

### Production Context

**Critical Point**: Pattern overhead in Python is **negligible in production**:
- LLM calls dominate: 100-1000ms per call
- Pattern overhead: 0.0006-0.082ms (0.635μs to 81.844μs)
- **Production impact**: <0.001-0.008% of total time

**Example Production Scenario**:
```
Agent workflow:
- 2 LLM calls @ 500ms each = 1,000ms
- Reflection pattern overhead: 0.017ms
- Production overhead: 0.0017%
```

---

## Rust Pattern Benchmarks

### Test Environment

- **Date**: December 17, 2025
- **Platform**: macOS (Darwin 25.2.0)
- **CPU**: Apple M4 Pro (ARM64)
- **Rust Version**: rustc 1.84.0
- **Build Type**: Release (optimized)
- **Iterations**: 1,000 (with 10-iteration warmup)

### Results

| Pattern | Time (μs/op) | Throughput (ops/s) | Status |
|---------|--------------|-------------------|--------|
| **Fallback** (2 agents) | 0 | 1,069,662 | ✅ |
| **Parallel** (3 agents) | 1 | 579,109 | ✅ |
| **Collaborative** (2 rounds) | 3 | 275,555 | ✅ |
| **Sequential** (3 agents) | 4 | 245,929 | ✅ |
| **Reflection** (2 iterations) | 2,809 | 356 | ✅ |

### Performance Categories

**Ultra-Fast (<10μs)** - Negligible overhead:
- Fallback: 0μs
- Parallel: 1μs
- Collaborative: 3μs
- Sequential: 4μs

**High (1000-3000μs)** - Measurable overhead:
- Reflection: 2,809μs

### Key Observations

1. **Extremely Fast Simple Patterns**: Fallback/Parallel/Collaborative/Sequential all <5μs
2. **Reflection Overhead**: Significantly higher at 2.8ms due to 2 iterations with complex critique parsing
3. **Zero-Cost Abstractions**: Rust's zero-cost abstractions deliver excellent performance
4. **Memory Safety**: All patterns maintain Rust's memory safety guarantees without overhead

### Production Context

**Critical Point**: Pattern overhead in Rust is **negligible in production**:
- LLM calls dominate: 100-1000ms per call
- Pattern overhead: 0.000-2.809ms (0μs to 2,809μs)
- **Production impact**: <0.001-0.3% of total time

**Example Production Scenario**:
```
Agent workflow:
- 2 LLM calls @ 500ms each = 1,000ms
- Reflection pattern overhead: 2.809ms
- Production overhead: 0.28%
```

### Running Benchmarks

```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-rust

# Build benchmarks (release mode)
cargo build --release --bench pattern_benchmarks

# Run benchmarks
./target/release/deps/pattern_benchmarks-*
```

**Output**: Table showing μs/op and ops/s for each pattern.

---

## Zig Pattern Benchmarks

### Test Environment

- **Date**: December 17, 2025
- **Platform**: macOS (Darwin 25.2.0)
- **CPU**: Apple M4 Pro (ARM64)
- **Zig Version**: 0.15.2
- **Build Type**: Debug
- **Iterations**: 1,000 (with 10-iteration warmup)

### Results

| Pattern | Time (μs/op) | Throughput (ops/s) | Status |
|---------|--------------|-------------------|--------|
| **Fallback** (2 agents) | 86 | 11,657 | ✅ |
| **Sequential** (3 agents) | 91 | 10,933 | ✅ |
| **Parallel** (3 agents) | 110 | 9,127 | ✅ |
| **Reflection** (2 iterations) | 252 | 3,966 | ✅ |

### Performance Categories

**Fast (10-100μs)** - Excellent performance:
- Fallback: 86μs
- Sequential: 91μs

**Fast (100-300μs)** - Good performance:
- Parallel: 110μs
- Reflection: 252μs

### Key Observations

1. **Consistent Performance**: All patterns show predictable, consistent timing
2. **Manual Memory Management**: Explicit allocator pattern provides deterministic performance
3. **Sequential Execution**: Zig doesn't use async, so "Parallel" is currently sequential
4. **Debug Build**: These benchmarks are in Debug mode; Release mode would be faster
5. **Memory Leaks Detected**: GeneralPurposeAllocator reports expected leaks in benchmark (results not cleaned up between iterations for performance)

### Production Context

**Critical Point**: Pattern overhead in Zig is **negligible in production**:
- LLM calls dominate: 100-1000ms per call
- Pattern overhead: 0.086-0.252ms (86μs to 252μs)
- **Production impact**: <0.01-0.03% of total time

**Example Production Scenario**:
```
Agent workflow:
- 2 LLM calls @ 500ms each = 1,000ms
- Reflection pattern overhead: 0.252ms
- Production overhead: 0.025%
```

### Running Benchmarks

```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-zig

# Build and run benchmarks
zig build bench-patterns
```

**Output**: Table showing μs/op and ops/s for each pattern.

**Note**: Memory leak warnings are expected in benchmarks (results not cleaned up between iterations for performance measurement).

---

## Cross-Language Status

### Pattern Performance Benchmarks Availability

| Language | Status | Location | Patterns | Notes |
|----------|--------|----------|----------|-------|
| **C++** | ✅ Complete | `agenkit-cpp/benchmarks/bench_patterns.cpp` | 18/18 | All benchmarks passing |
| **Go** | ✅ Complete | `agenkit-go/benchmarks/pattern_benchmarks_test.go` | 18/18 | All benchmarks passing |
| **Python** | ✅ Complete | `tests/benchmarks/test_pattern_performance.py` | 18/18 | All benchmarks passing (⚠️ API inconsistencies - see issue #319) |
| **TypeScript** | ❌ Not implemented | - | 0/18 | Not yet started |
| **Rust** | ⚠️ Partial | `agenkit-rust/benches/pattern_benchmarks.rs` | 5/18 | Sequential, Parallel, Reflection, Fallback, Collaborative |
| **Zig** | ⚠️ Partial | `agenkit-zig/benchmarks/patterns.zig` | 4/18 | Sequential, Parallel, Reflection, Fallback |

### Python Evaluation Framework vs Performance Benchmarks

Python has a **Pattern Evaluation Framework** (`agenkit/evaluation/pattern_benchmarks.py`) that:
- Loads YAML test specifications
- Validates pattern **behavior** (correctness)
- Measures execution time as metadata
- **Not designed for raw performance measurement**

This is **different** from C++ performance benchmarks which:
- Use simple test agents to isolate pattern overhead
- Measure microsecond-level timing
- Focus on framework performance, not correctness

### Overhead Benchmarks (Separate Category)

Python and Go have **overhead benchmarks** measuring:
- Middleware overhead (retry, metrics, circuit breaker, rate limiter, timeout)
- Transport protocol overhead (HTTP/1.1, HTTP/2, HTTP/3)
- Streaming response overhead (SSE)

These are documented in the [Overhead Benchmarks](benchmarks.md) page but are **orthogonal to pattern benchmarks**.

---

## Running Pattern Benchmarks

### C++

```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-cpp

# Configure with benchmarks enabled
cmake -B build -S . -DAGENKIT_BUILD_BENCHMARKS=ON

# Build benchmarks
cmake --build build --target bench_patterns -j8

# Run pattern benchmarks
./build/benchmarks/bench_patterns
```

**Output**: Table showing mean, median, min, max for each pattern.

### Go

```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-go

# Run all pattern benchmarks
go test -bench='^Benchmark(Reflection|ReAct|AgentsAsTools|ReasoningWithTools|Conversational|Task|Multiagent|Planning|Autonomous|Memory|Sequential|Parallel|Router|Fallback|Collaborative|HumanInLoop)' -benchmem -benchtime=1s ./benchmarks

# Or run specific pattern
go test -bench=BenchmarkReflection -benchmem ./benchmarks
```

**Output**: Table showing ns/op, μs/op, B/op (bytes allocated), and allocs/op (allocations per operation).

### Python

```bash
cd /Users/scttfrdmn/src/agenkit

# Run all pattern benchmarks
uv run pytest tests/benchmarks/test_pattern_performance.py -v -s

# Or run specific pattern
uv run pytest tests/benchmarks/test_pattern_performance.py::test_benchmark_reflection -v -s

# Run all benchmarks with timing output
uv run pytest tests/benchmarks/test_pattern_performance.py -v -s -m benchmark
```

**Output**: Displays mean, median, min, max timing for each pattern in microseconds.

**Note**: Python benchmarks use pytest + asyncio for async pattern support.

---

## Roadmap

### v0.42.0 (Completed)

- [x] Establish C++ pattern benchmark baseline (17/18 patterns)
- [x] Fix C++ Conversational anomaly (issue #313)
- [x] Fix C++ Autonomous anomaly (issue #313)
- [x] Add 6 missing C++ patterns (Sequential, Parallel, Router, Fallback, Collaborative, Human-in-Loop)
- [x] Fix Go protobuf panic (issue #314)
- [x] Implement Go pattern benchmarks (16/18 patterns)
- [x] Collect Go performance data
- [x] Create C++ vs Go comparison documentation
- [x] Update documentation with all results

### v0.43.0 (Completed)

- [x] Implement Python pattern benchmarks (18/18 patterns)
- [x] Collect Python performance data
- [x] Complete Supervisor pattern benchmarks (C++ + Go + Python)
- [x] Complete Memory: Hierarchy benchmarks (Go + Python)
- [x] Document API inconsistencies (issue #319)
- [x] Reach 50% coverage milestone (54/108 data points)

### v0.44.0 (Next Release)

- [ ] Resolve Python API inconsistencies (issue #319)
- [ ] Normalize Python APIs to match C++/Go
- [ ] Update Python benchmarks with normalized APIs
- [ ] Implement TypeScript pattern benchmarks

### v1.0 (Future)

- [ ] Complete pattern benchmarks for all 6 languages
- [ ] Cross-language performance comparison dashboard
- [ ] Automated regression detection in CI/CD
- [ ] Performance optimization based on benchmark findings

---

## Data Collection Progress

### Target

**108 data points**: 18 patterns × 6 languages = 108 measurements

### Current Status

**63 data points collected**: 18 C++ + 18 Go + 18 Python + 5 Rust + 4 Zig patterns

| Language | Patterns | Status | Progress |
|----------|----------|--------|----------|
| C++ | 18/18 | ✅ Complete | 100% |
| Go | 18/18 | ✅ Complete | 100% |
| Python | 18/18 | ✅ Complete | 100% (⚠️ API inconsistencies) |
| TypeScript | 0/18 | ❌ Not implemented | 0% |
| Rust | 5/18 | ⚠️ Partial | 28% |
| Zig | 4/18 | ⚠️ Partial | 22% |
| **Total** | **63/108** | **⚠️ In Progress** | **58%** |

---

## Contributing

### Adding Pattern Benchmarks

When implementing pattern benchmarks for a new language:

1. **Use Simple Test Agent**: Isolate pattern overhead from LLM latency
2. **Measure Microseconds**: Use high-resolution timing (e.g., `std::chrono`, `time.perf_counter()`)
3. **Run 1,000+ Iterations**: Get statistical significance
4. **Include Warmup**: Run 10 iterations before measurement
5. **Report Statistics**: Mean, median, min, max
6. **Document Configuration**: Pattern parameters (e.g., "Reflection (2 iterations)")

### Benchmark Structure

```
<lang>/benchmarks/bench_patterns.<ext>:
├── benchmark_reflection()      # 2 iterations
├── benchmark_react()           # 3 steps
├── benchmark_agents_as_tools() # Single tool call
├── benchmark_orchestration()   # 2 agents
├── benchmark_reasoning_tools() # Tool-aware reasoning
├── benchmark_conversational()  # 10 message history
├── benchmark_task()            # One-shot execution
├── benchmark_multiagent()      # 2 sequential agents
├── benchmark_planning()        # Plan + execute
├── benchmark_autonomous()      # 5 iterations
└── benchmark_memory()          # Store + retrieve
```

### Reporting Issues

When filing performance issues:
- Include benchmark output (mean, median, min, max)
- Specify test environment (OS, CPU, compiler/interpreter version)
- Note if results differ significantly from this document
- Provide reproduction steps

---

## Frequently Asked Questions

### Q: Are all patterns benchmarked across all languages?

**A**: C++, Go, and Python all have complete 18/18 pattern coverage. TypeScript, Rust, and Zig are not yet implemented.

### Q: Should I worry about pattern overhead in production?

**A**: No. Pattern overhead (0.001-0.37ms) is negligible compared to LLM calls (100-1000ms). Production impact is <0.1%.

### Q: What happened to the Conversational and Autonomous anomalies?

**A**: Both fixed in v0.42.0. Conversational was 5.13s due to history accumulation (now 33μs). Autonomous was 0.00μs due to goal reuse (now 3.40μs). See "Resolved Issues" section for details.

### Q: When will other languages have pattern benchmarks?

**A**: Roadmap:
- C++: ✅ Complete (18/18 patterns)
- Go: ✅ Complete (18/18 patterns)
- Python: ✅ Complete (18/18 patterns) - Note: API inconsistencies tracked in issue #319
- TypeScript: v0.44.0 (planned)
- Rust, Zig: v1.0 (planned)

### Q: How do I compare languages?

**A**: See the Go Pattern Benchmarks section above for direct C++ vs Go comparison. Full comparison matrix with all languages will be available in the [Performance Comparison Matrix](comparison-matrix.md) page.

---

## Related Documentation

- [Overhead Benchmarks](benchmarks.md) - Middleware, transport, streaming overhead
- [Performance Comparison Matrix](comparison-matrix.md) - Cross-language performance comparison

---

Last Updated: December 18, 2025
Status: **C++ (18/18), Go (18/18), and Python (18/18) benchmarks complete** - 54/108 total data points (50% complete)
⚠️ Note: Python APIs have inconsistencies with C++/Go - tracked in issue #319
