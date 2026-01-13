# Rust Performance Baseline (v0.46.0)

**Date**: January 13, 2026
**Issue**: #365 - Rust Performance Optimization
**Benchmark Tool**: Criterion v0.5.1

## Executive Summary

This document captures the baseline performance metrics for the Agenkit Rust implementation before optimization work. These measurements will serve as a reference point for evaluating the impact of future optimizations.

## Environment

- **Platform**: macOS (Darwin 25.2.0)
- **Rust Version**: 1.84+ (2021 edition)
- **Build Profile**: Release (`--release`)
- **CPU**: Apple Silicon (hardware concurrency optimized)

## Benchmark Results

### Pattern Performance

#### Sequential Pattern (Linear Agent Chaining)
Scales linearly with agent count as expected:

| Agents | Mean Time | Throughput |
|--------|-----------|------------|
| 1      | 2.03 µs   | ~493K ops/s |
| 2      | 3.30 µs   | ~303K ops/s |
| 3      | 4.17 µs   | ~240K ops/s |
| 5      | 7.29 µs   | ~137K ops/s |
| 10     | 10.14 µs  | ~99K ops/s  |

**Summary**: ~2.0µs base overhead + ~0.8µs per agent

#### Parallel Pattern (Concurrent Agent Execution)
Better scaling than sequential due to concurrent execution:

| Agents | Mean Time | Throughput |
|--------|-----------|------------|
| 1      | 1.74 µs   | ~575K ops/s |
| 2      | 2.86 µs   | ~350K ops/s |
| 3      | 2.89 µs   | ~346K ops/s |
| 5      | 3.45 µs   | ~290K ops/s |
| 10     | 7.34 µs   | ~136K ops/s |

**Summary**: ~1.7µs base overhead, better parallelization up to 5 agents

#### Reflection Pattern (Iterative Refinement)
Higher overhead due to generation-critique cycles:

| Iterations | Mean Time |
|------------|-----------|
| 1          | 2.91 ms   |
| 2          | 4.91 ms   |
| 3          | 5.08 ms   |
| 5          | 5.09 ms   |

**Summary**: ~3ms for single iteration, ~5ms for multi-iteration (diminishing returns)

#### Fallback Pattern (Error Recovery)
Minimal overhead for success path:

| Configuration | Mean Time | Throughput |
|---------------|-----------|------------|
| 2 agents      | 2.28 µs   | ~439K ops/s |

#### Collaborative Pattern (Multi-Round Consensus)
Exponential growth with rounds (expected):

| Rounds | Mean Time | Throughput |
|--------|-----------|------------|
| 1      | 4.28 µs   | ~234K ops/s |
| 2      | 10.56 µs  | ~95K ops/s  |
| 3      | 16.77 µs  | ~60K ops/s  |
| 5      | 49.05 µs  | ~20K ops/s  |

**Summary**: ~4µs base + exponential growth per round

### Core Operations Performance

#### Message Operations (Nanosecond Scale)
Extremely efficient core operations:

| Operation       | Mean Time | Throughput |
|-----------------|-----------|------------|
| create_text     | 147 ns    | ~6.8M ops/s |
| clone           | 69 ns     | ~14.4M ops/s |
| content_as_str  | 2.2 ns    | ~453M ops/s |

**Key Finding**: Message operations are **not** a bottleneck (nanosecond scale)

#### Metadata Operations

| Operation       | Mean Time | Throughput |
|-----------------|-----------|------------|
| with_metadata   | 346 ns    | ~2.9M ops/s |
| get_metadata    | 34 ns     | ~30M ops/s |

### Pattern Benchmarks Summary

From the simple pattern benchmarks (non-statistical):

| Pattern       | Time/Op | Throughput |
|---------------|---------|------------|
| Sequential    | 2 µs    | 335K ops/s |
| Parallel      | 2 µs    | 344K ops/s |
| Reflection    | 4603 µs | 217 ops/s  |
| Fallback      | 1 µs    | 596K ops/s |
| Collaborative | 9 µs    | 103K ops/s |

## Key Insights

### Strengths
1. **Core Operations**: Message creation/cloning/access are extremely fast (nanoseconds)
2. **Simple Patterns**: Sequential and parallel patterns have low overhead (~2µs)
3. **Fallback**: Minimal error-handling overhead (~1µs)

### Optimization Opportunities
1. **Reflection Pattern**: 3-5ms per iteration is high - potential for caching optimization
2. **Collaborative Pattern**: Exponential growth with rounds - opportunity for parallel round execution
3. **Allocation**: While not measured directly, string operations likely account for overhead

### Comparison to Other Languages
- **vs Python**: Rust is likely 10-100x faster for these operations
- **vs Go**: Expected to be comparable (both compiled, similar performance characteristics)
- **vs C++**: Expected to be comparable with similar optimization levels

## Optimization Roadmap

Based on these baselines, the following optimizations are prioritized:

### Phase 1: Completed ✅
- [x] Criterion benchmark infrastructure
- [x] LRU caching implementation
- [x] Async memoization implementation

### Phase 2: Memory Optimizations (Next)
- [ ] Reduce string allocations
- [ ] String interning for common values
- [ ] Arena allocation for short-lived objects
- [ ] Profile memory usage with `cargo flamegraph`

### Phase 3: Concurrency Optimizations
- [ ] Lock-free data structures (crossbeam)
- [ ] Parallel message processing (rayon)
- [ ] Work-stealing for pattern execution

### Phase 4: Algorithm Optimizations
- [ ] Optimize reflection pattern with early termination
- [ ] Parallel collaborative rounds
- [ ] Smart caching for deterministic agents

## Testing the Optimizations

To verify improvements after implementing optimizations:

```bash
# Run full benchmark suite
cargo bench

# Run specific benchmark
cargo bench --bench criterion_benchmarks sequential

# Compare against baseline (after changes)
cargo bench --bench criterion_benchmarks -- --save-baseline after
critcmp before after

# Generate flamegraph for profiling
cargo flamegraph --bench criterion_benchmarks
```

## Regression Detection

Criterion automatically detects performance regressions:
- **Threshold**: ±5% variation triggers warning
- **Statistical Analysis**: 100 samples, confidence intervals reported
- **Outlier Detection**: Automatically identifies and reports outliers

## Notes

- All benchmarks use release builds (`--release`)
- Measurements are in **microseconds (µs)** for patterns, **nanoseconds (ns)** for core ops
- Throughput calculated as `1 / mean_time`
- Standard deviation and outliers are tracked but not shown here (see Criterion HTML reports)
- HTML reports available in `target/criterion/` after running benchmarks

## Next Steps

1. **Memory Profiling**: Use `cargo-flamegraph` to identify allocation hotspots
2. **Implement Caching Tests**: Verify LRU/Memoization performance gains
3. **Cross-Language Comparison**: Benchmark Python/Go equivalents for comparison
4. **Production Metrics**: Add telemetry to track real-world performance

---

*Generated from Issue #365 baseline measurements*
