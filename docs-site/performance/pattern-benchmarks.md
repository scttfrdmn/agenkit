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
| **ReAct** (3 steps) | 0.92 | 1.00 | 0.00 | 8.00 | 1,000 | ✅ |
| **Orchestration** (2 agents) | 1.05 | 1.00 | 0.00 | 5.00 | 1,000 | ✅ |
| **Agents-as-Tools** (call) | 2.28 | 2.00 | 2.00 | 12.00 | 1,000 | ✅ |
| **Task** (one-shot) | 3.25 | 3.00 | 3.00 | 17.00 | 1,000 | ✅ |
| **Planning** (plan + execute) | 8.78 | 9.00 | 8.00 | 9.00 | 1,000 | ✅ |
| **Multiagent** (2 sequential) | 9.91 | 9.00 | 9.00 | 54.00 | 1,000 | ✅ |
| **Reflection** (2 iterations) | 56.52 | 49.00 | 46.00 | 176.00 | 1,000 | ✅ |
| **Reasoning with Tools** | 419.86 | 382.00 | 325.00 | 853.00 | 1,000 | ✅ |
| **Memory: Working** (store) | 0.02 | 0.00 | 0.00 | 2.00 | 1,000 | ✅ |
| **Memory: Working** (retrieve) | 1.46 | 1.00 | 1.00 | 3.00 | 1,000 | ✅ |
| **Memory: Hierarchy** (store) | 1.00 | 1.00 | 1.00 | 1.00 | 1,000 | ✅ |
| **Memory: Hierarchy** (retrieve) | 6.13 | 6.00 | 6.00 | 9.00 | 1,000 | ✅ |
| **Conversational** (10 history) | 5,134,570.70 | 1,371,544.00 | 46,129.00 | 26,244,289.00 | 10 | ⚠️ Anomaly |
| **Autonomous** (5 iterations) | 0.00 | 0.00 | 0.00 | 0.00 | 10 | ⚠️ Anomaly |

### Performance Categories

**Ultra-Fast (<10μs)** - Negligible overhead:
- ReAct: 0.92μs
- Orchestration: 1.05μs
- Agents-as-Tools: 2.28μs
- Task: 3.25μs
- Planning: 8.78μs
- Multiagent: 9.91μs
- Memory operations: 0.02-6.13μs

**Fast (10-100μs)** - Excellent performance:
- Reflection: 56.52μs

**Moderate (100-1000μs)** - Acceptable overhead:
- Reasoning with Tools: 419.86μs

### Known Issues

#### Conversational Pattern Anomaly

**Observed**: 5.13 **seconds** mean latency (5,134,570μs)
**Expected**: <1ms (<1,000μs)

**Root Cause Analysis**:
- Benchmark uses only 10 iterations (vs 1,000 for other patterns)
- Comment in code: "Reduced to 10 iterations to prevent memory buildup"
- History accumulates across iterations causing cumulative slowdown
- By iteration 10, history management overhead dominates

**Impact**:
- Indicates potential memory leak or inefficient history management
- Real-world impact depends on conversation length
- Production systems may experience degradation over long conversations

**Remediation**:
- [ ] Fix history management in ConversationalAgent
- [ ] Reset history between benchmark iterations
- [ ] Add memory profiling to identify leak source
- [ ] Re-run benchmark after fix

#### Autonomous Pattern Anomaly

**Observed**: 0.00μs (no measurable time)
**Expected**: >10μs (some overhead for goal processing)

**Root Cause Analysis**:
- `autonomous.run()` may return immediately without executing work
- Timing measurement may not capture async work
- Goals may be marked as complete without processing

**Impact**:
- Benchmark not measuring actual autonomous agent execution
- Cannot assess autonomous pattern performance

**Remediation**:
- [ ] Verify autonomous agent actually processes goals
- [ ] Check if `run()` is async and timing misses work
- [ ] Add instrumentation to confirm goal execution
- [ ] Re-run benchmark after fix

### Production Context

**Critical Point**: Pattern overhead is **negligible in production** because:
- LLM calls dominate execution time: 100-1000ms per call
- Pattern overhead: 0.001-0.42ms (excluding anomalies)
- **Production impact**: <0.01-0.1% of total time

**Example Production Scenario**:
```
Agent workflow:
- 2 LLM calls @ 500ms each = 1,000ms
- Reflection pattern overhead: 0.056ms
- Production overhead: 0.0056%
```

The benefits of patterns (code clarity, reusability, maintainability) vastly outweigh the minimal performance cost.

---

## Cross-Language Status

### Pattern Performance Benchmarks Availability

| Language | Status | Location | Patterns | Notes |
|----------|--------|----------|----------|-------|
| **C++** | ✅ Implemented | `agenkit-cpp/benchmarks/bench_patterns.cpp` | 12/18 | 2 anomalies pending fix |
| **Go** | ❌ Blocked | - | 0/18 | Protobuf panic blocks all tests |
| **Python** | ❌ Not found | - | 0/18 | Has evaluation framework only |
| **TypeScript** | ❓ Unknown | - | 0/18 | Not investigated |
| **Rust** | ❓ Unknown | - | 0/18 | Not investigated |
| **Zig** | ❓ Unknown | - | 0/18 | Not investigated |

### Go Protobuf Blocker

**Issue**: All Go tests and benchmarks fail with protobuf deserialization panic:
```
panic: runtime error: slice bounds out of range [-5:]
google.golang.org/protobuf/internal/filedesc.(*File).unmarshalSeed
```

**Impact**:
- Blocks all Go benchmark execution
- Blocks Go pattern performance measurements
- Blocks C++ vs Go comparison

**Investigation Needed**:
- Protobuf version mismatch
- Corrupted generated code
- Need to regenerate protobuf files from `/Users/scttfrdmn/src/agenkit/proto/agent.proto`

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

### Go (Blocked - Pending Protobuf Fix)

**Note**: Currently blocked by protobuf panic. After fix:

```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-go

# Run pattern benchmarks (once implemented)
go test -bench=BenchmarkPattern -benchmem ./benchmarks
```

### Python (Not Yet Implemented)

Pattern performance benchmarks need to be created. Suggested structure:

```python
# benchmarks/test_pattern_performance.py
import time
from agenkit.patterns import ReflectionAgent, ReActAgent
from tests.mocks import EchoAgent

def measure_pattern(pattern_fn, iterations=1000):
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        pattern_fn()
        times.append((time.perf_counter() - start) * 1_000_000)  # μs
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times)
    }

def test_reflection_performance():
    agent = EchoAgent()
    reflection = ReflectionAgent(agent, max_iterations=2)

    result = measure_pattern(
        lambda: reflection.process(Message(role="user", content="test"))
    )

    assert result["mean"] < 1000  # <1ms threshold
    print(f"Reflection: {result['mean']:.2f}μs")
```

---

## Roadmap

### v0.42.0 (Current Release)

- [x] Establish C++ pattern benchmark baseline
- [ ] Fix C++ Conversational anomaly (issue #XXX)
- [ ] Fix C++ Autonomous anomaly (issue #XXX)
- [ ] Fix Go protobuf panic (issue #XXX)
- [ ] Document current state in this file

### v0.43.0 (Next Release)

- [ ] Implement Go pattern benchmarks
- [ ] Collect Go performance data
- [ ] Create C++ vs Go comparison matrix
- [ ] Implement Python pattern benchmarks
- [ ] Investigate remaining languages (TS, Rust, Zig)

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

**14 data points collected**: 12 valid C++ patterns + 2 anomalies

| Language | Patterns | Status | Progress |
|----------|----------|--------|----------|
| C++ | 12/18 | ✅ Partial | 67% |
| Go | 0/18 | ❌ Blocked | 0% |
| Python | 0/18 | ❌ Not implemented | 0% |
| TypeScript | 0/18 | ❓ Unknown | 0% |
| Rust | 0/18 | ❓ Unknown | 0% |
| Zig | 0/18 | ❓ Unknown | 0% |
| **Total** | **12/108** | **⚠️ In Progress** | **11%** |

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

### Q: Why are some patterns missing from C++ benchmarks?

**A**: C++ has implemented 12/18 patterns with benchmarks. Missing patterns:
- Sequential
- Parallel
- Router
- Fallback
- Collaborative
- Human-in-Loop

These patterns exist but don't have performance benchmarks yet.

### Q: Should I worry about pattern overhead in production?

**A**: No. Pattern overhead (0.001-0.42ms) is negligible compared to LLM calls (100-1000ms). Production impact is <0.1%.

### Q: Why does Conversational show 5 seconds?

**A**: Known anomaly. History accumulates across benchmark iterations causing cumulative slowdown. Does not reflect real-world single-call performance. Fix pending.

### Q: When will other languages have pattern benchmarks?

**A**: Roadmap:
- Go: v0.43.0 (after protobuf fix)
- Python: v0.43.0
- TypeScript, Rust, Zig: v1.0

### Q: How do I compare languages?

**A**: Once Go benchmarks are implemented, we'll publish a comparison matrix showing relative performance (C++ baseline = 1.0x, Go = Xx, Python = Yx).

---

## Related Documentation

- [Overhead Benchmarks](benchmarks.md) - Middleware, transport, streaming overhead
- [Performance Comparison Matrix](comparison-matrix.md) - Cross-language performance comparison

---

Last Updated: December 17, 2025
Status: Initial baseline established (C++ only)
