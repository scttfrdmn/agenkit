# Pattern Performance Matrix - Cross-Language Comparison

**Date**: January 14, 2026
**Platform**: macOS (Darwin 25.2.0), Apple M4 Pro, ARM64
**Status**: 🚧 Partial - Python & Go Complete

---

## ⚠️ CRITICAL: Cross-Language Comparisons Are Invalid

**Issue**: GitHub #459 - Benchmark Methodology Flaw

The current Python and TypeScript benchmarks **do not test actual patterns**. They only measure mock agent echo latency, while Go, C++, and Zig benchmarks correctly test pattern implementations.

**What this means**:
- ❌ Python benchmarks measure `MockAgent.process()` echo only (1.5-3.5 μs)
- ❌ TypeScript benchmarks have the same issue
- ✅ Go, C++, Zig benchmarks measure actual pattern overhead (1-185 μs)
- ❌ **All cross-language comparisons below are meaningless**

**Status**: Python and TypeScript benchmarks must be rewritten to test actual patterns before any performance claims can be made. See `BENCHMARK_METHODOLOGY_ISSUE.md` for full analysis.

**Use Case**: Each language's internal benchmarks are still valid for tracking regressions within that language.

---

## Executive Summary

This document provides a comprehensive performance comparison of all agent patterns across Agenkit's 6 language implementations. Performance benchmarks measure **framework overhead only** using mock agents to isolate pattern logic from LLM latency.

**Current Status**:
- ✅ **Python**: 17/21 patterns benchmarked
- ✅ **Go**: 4/21 patterns benchmarked (core patterns)
- ⚠️ **TypeScript**: Implementation exists but needs dependency fixes
- ⚠️ **Rust**: No pattern benchmarks found
- ⚠️ **C++**: Benchmarks not built/accessible
- ⚠️ **Zig**: No benchmark command configured

---

## Performance Comparison (Python vs Go)

⚠️ **WARNING: These comparisons are invalid - see issue #459**

### Core Patterns

| Pattern | Python (μs) | Go (μs) | Comparison | Python Ops/sec | Go Ops/sec |
|---------|-------------|---------|------------|----------------|------------|
| **Reflection** | 1.59 ❌ | 185.2 ✅ | ❌ **Invalid** (Python tests echo only) | 627,336 | 5,399 |
| **ReAct** | 2.36 ❌ | 1.93 ✅ | ❌ **Invalid** (Python tests echo only) | 423,139 | 518,135 |
| **Sequential** | 1.79 ❌ | 1.25 ✅ | ❌ **Invalid** (Python tests echo only) | 558,724 | 800,000 |
| **Parallel** | 1.88 ❌ | 5.21 ✅ | ❌ **Invalid** (Python tests echo only) | 533,097 | 191,938 |

**Note**: Python numbers are NOT pattern overhead - they measure `MockAgent.process()` echo latency only. Go numbers correctly measure actual pattern implementations. These cannot be compared.

### All Python Patterns (Sorted by Performance)

⚠️ **WARNING: These are MockAgent echo latencies, NOT pattern overhead**

| Rank | Pattern | Avg Time (μs) | Ops/sec | Category |
|------|---------|---------------|---------|----------|
| 1 | Conversational | 1.52 | 659,359 | Core |
| 2 | Reasoning with Tools | 1.56 | 642,226 | Reasoning |
| 3 | Router | 1.56 | 639,267 | Orchestration |
| 4 | Agents as Tools | 1.57 | 637,891 | Advanced |
| 5 | Planning | 1.59 | 630,285 | Advanced |
| 6 | Reflection | 1.59 | 627,336 | Core |
| 7 | Sequential | 1.79 | 558,724 | Core |
| 8 | Parallel | 1.88 | 533,097 | Core |
| 9 | Orchestration | 1.91 | 523,880 | Orchestration |
| 10 | Autonomous | 1.99 | 503,504 | Orchestration |
| 11 | Supervisor | 2.30 | 433,949 | Advanced |
| 12 | Human in Loop | 2.32 | 430,532 | Advanced |
| 13 | ReAct | 2.36 | 423,139 | Core |
| 14 | Collaborative | 2.45 | 407,823 | Advanced |
| 15 | Fallback | 3.00 | 333,380 | Orchestration |
| 16 | Multiagent | 3.02 | 330,838 | Orchestration |
| 17 | Task | 3.59 | 278,678 | Core |

**Python Statistics**:
- **Average**: 2.12 μs across all patterns
- **Fastest**: Conversational (1.52 μs, 659k ops/sec)
- **Slowest**: Task (3.59 μs, 279k ops/sec)
- **Range**: 2.4x difference between fastest and slowest

---

## Key Findings

⚠️ **Most findings below are based on invalid comparisons - see issue #459**

### 1. Go Reflection Performance Fix ✅

**Issue** (Resolved): Go Reflection was initially slow (247.8 μs)

**Note**: The "156x slower than Python" comparison was invalid because Python was only testing echo latency, not the Reflection pattern.

**Root Cause**: `regexp.MustCompile()` called in hot loop (90,432 times per benchmark run)

**Fix Applied**: Pre-compiled regex patterns at package level

**Results**:
- Time: **25% faster** (247.8 μs → 185.2 μs)
- Memory: **80% reduction** (35 KB → 7 KB per operation)
- Allocations: **85% fewer** (298 → 46 allocs/op)

**Current Status**: Go Reflection runs at 185.2 μs for the actual pattern implementation:
- Reflection runs 2 full iterations (generate + critique + parse + refine)
- Each critique requires regex matching (40-50 μs per parse due to backtracking)
- String formatting for prompts adds overhead (15-20 μs per prompt)
- Total: ~90-100 μs per iteration × 2 = ~180-200 μs ✅

**In Production**: Pattern overhead is negligible (<0.02% of LLM call latency)

**See**: `GO_REFLECTION_FIX_SUMMARY.md` and `PERFORMANCE_ANALYSIS_GO_REFLECTION.md` for full analysis

### 2. Python Consistency ❌ INVALID

**Finding**: All Python patterns execute in **1.5-3.6 μs range** (2.4x spread)

**❌ RETRACTED**: This finding is invalid - Python benchmarks only test `MockAgent.process()` echo latency, NOT actual patterns. The consistency simply reflects that echo operations have similar performance.

**Actual Pattern Overhead**: Unknown - benchmarks need to be rewritten.

### 3. Go Sequential Pattern Excellence ❌ INVALID COMPARISON

**Finding**: Go Sequential is **2.01x faster** than Python (0.89 μs vs 1.79 μs)

**❌ RETRACTED**: This comparison is meaningless - Python benchmark tests echo latency only, not the Sequential pattern.

**Go Sequential** (valid): 1.25 μs for actual pattern with low allocation overhead (1,848 B/op, 21 allocs/op)

### 4. Throughput Comparison ❌ INVALID

| Language | Min Ops/sec | Max Ops/sec | Average |
|----------|-------------|-------------|---------|
| Python ❌ | 278,678 | 659,359 | 471,872 |
| Go (measured) ✅ | 4,035 | 1,122,334 | 477,219 |

**❌ RETRACTED**: Python numbers are echo latencies only, not pattern throughput. These cannot be compared to Go's actual pattern measurements.

---

## Memory Efficiency (Go Only)

Go benchmarks include memory allocation data:

| Pattern | Memory (B/op) | Allocations (/op) | Efficiency |
|---------|---------------|-------------------|------------|
| Sequential | 1,848 | 21 | ✅ Excellent |
| Parallel | 1,281 | 20 | ✅ Excellent |
| ReAct | 1,488 | 14 | ✅ Excellent |
| Reflection | 34,991 | 298 | ⚠️ High |

**Analysis**:
- Most patterns: **<2KB memory, <25 allocations** (highly efficient)
- Reflection: **17-27x more memory** than other patterns (needs optimization)

---

## Production Context

### Why Microsecond Overhead Doesn't Matter

For typical LLM-based agent workflows:
- **Agent work**: 100-5,000ms (LLM calls, I/O, tool execution)
- **Pattern overhead**: 1-250μs (0.0002-0.05ms)
- **Overhead as % of total**: **0.0002% - 0.2%**

**Example**:
```
Typical ReAct agent with 3 LLM calls @ 500ms each:
- Total time: 1,500ms
- Pattern overhead (Python): 0.002ms (2.36 μs)
- Overhead percentage: 0.00013%
```

### When Performance Differences Matter

Pattern performance becomes relevant for:
1. **High-frequency, low-latency scenarios** (>1000 requests/sec)
2. **Large-scale batch processing** (millions of pattern executions)
3. **Embedded/edge deployments** (resource-constrained)
4. **Micro-benchmarking** (isolating framework overhead)

For 99% of production use cases, **any language choice performs excellently**.

---

## Language Recommendations

### Choose Based on Your Priorities:

**Python** - Best for:
- ✅ Rapid development and prototyping
- ✅ Extensive ML/AI ecosystem integration
- ✅ Consistent, predictable performance across patterns
- ✅ Team familiarity with async Python

**Go** - Best for:
- ✅ High-throughput, low-latency services
- ✅ Compiled binaries with no runtime dependencies
- ✅ Excellent sequential pattern performance (2x faster)
- ✅ Production deployments requiring memory efficiency

**TypeScript** - Best for:
- ✅ Full-stack JavaScript/TypeScript projects
- ✅ Frontend agent integration
- ✅ Node.js ecosystem familiarity
- ⏳ Benchmarks pending

**Rust** - Best for:
- ✅ Maximum performance and memory safety
- ✅ Systems-level integration
- ✅ Zero-cost abstractions
- ⏳ Benchmarks needed

**C++** - Best for:
- ✅ Legacy C++ codebases
- ✅ SIMD optimization opportunities (4-8x on x86_64)
- ✅ Embedded/real-time systems
- ⏳ Benchmark data collection in progress

**Zig** - Best for:
- ✅ C interop requirements
- ✅ Explicit memory control
- ✅ Compile-time execution
- ⏳ Benchmarks needed

---

## Next Steps

### Immediate (This Sprint)

1. ✅ **Python benchmarks** - Complete (17/21 patterns)
2. ✅ **Go core patterns** - Complete (4/21 patterns)
3. 🔲 **Investigate Go Reflection anomaly** - Profile and optimize
4. 🔲 **Complete Go pattern coverage** - Implement remaining 17 patterns

### Short-term (Next Sprint)

5. 🔲 **Fix TypeScript benchmarks** - Resolve dependency issues
6. 🔲 **Implement Rust benchmarks** - Create benchmark suite
7. 🔲 **Build C++ benchmarks** - Make accessible and run
8. 🔲 **Add Zig benchmark command** - Configure build system

### Long-term (Future Releases)

9. 🔲 **CI integration** - Automated regression detection
10. 🔲 **Cross-platform testing** - Linux, Windows, ARM64 vs x86_64
11. 🔲 **Performance dashboard** - Visual tracking over time
12. 🔲 **Real LLM benchmarks** - End-to-end performance with actual models

---

## Benchmark Methodology

### Setup

**Mock Agents**: All benchmarks use simple echo agents that return input as output, eliminating LLM latency and focusing purely on framework overhead.

**Iterations**:
- Python: 1,000 iterations per pattern (warmup included)
- Go: 100 iterations per pattern (Go's benchmark framework includes warmup)

**Platform**: macOS (Darwin 25.2.0), Apple M4 Pro, ARM64, 12 cores, 48GB RAM

### Running Benchmarks

**Python**:
```bash
cd /Users/scttfrdmn/src/agenkit
uv run python benchmarks/python_pattern_benchmarks.py
```

**Go**:
```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-go/benchmarks
go test -bench=. -benchmem -benchtime=1000x
```

**TypeScript** (pending fix):
```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-ts
# TODO: Fix dependencies and add benchmark script
```

**Rust** (not implemented):
```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-rust
cargo bench --bench pattern_performance
```

**C++** (needs build):
```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/benchmarks/bench_patterns
```

**Zig** (not implemented):
```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-zig
zig build benchmark
```

---

## References

- **Middleware Benchmarks**: `/benchmarks/BASELINES.md`
- **Transport Benchmarks**: `/benchmarks/BASELINES.md` (Sections: Transport Protocol, Streaming)
- **C++ Optimizations**: `/docs/PERFORMANCE_COMPARISON.md`
- **Python Benchmarks Source**: `/benchmarks/python_pattern_benchmarks.py`
- **Go Benchmarks Source**: `/agenkit-go/benchmarks/pattern_benchmarks_test.go`

---

## Contributing

To add or improve pattern benchmarks:

1. Follow existing benchmark structure in your language
2. Use mock agents (not real LLMs)
3. Run 100-1000 iterations for statistical significance
4. Report mean, median, min, max, and standard deviation
5. Include memory/allocation data where available
6. Update this document with your results

---

**Last Updated**: January 14, 2026
**Version**: v0.44.0
**Status**: 🚧 In Progress - Python & Go complete, 4 languages pending
