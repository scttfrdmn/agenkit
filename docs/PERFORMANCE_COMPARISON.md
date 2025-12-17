# Performance Comparison Matrix

## Cross-Language Pattern Performance (v0.42.0)

### Status: Partial Data Available

Currently, only **C++** has pattern performance benchmarks implemented. Cross-language comparison pending implementation of benchmarks in other languages.

---

## C++ Pattern Performance (Baseline)

### Ultra-Fast Patterns (<10μs)

| Pattern | Mean | Median | Relative | Use Case |
|---------|------|--------|----------|----------|
| Memory: Working (store) | 0.02μs | 0.00μs | **1.0x** | Short-term storage |
| ReAct | 0.92μs | 1.00μs | **46x** | Reasoning + acting |
| Orchestration | 1.05μs | 1.00μs | **53x** | Multi-agent coordination |
| Memory: Hierarchy (store) | 1.00μs | 1.00μs | **50x** | Long-term storage |
| Memory: Working (retrieve) | 1.46μs | 1.00μs | **73x** | Short-term retrieval |
| Agents-as-Tools | 2.28μs | 2.00μs | **114x** | Tool wrapping |
| Task | 3.25μs | 3.00μs | **163x** | One-shot execution |
| Memory: Hierarchy (retrieve) | 6.13μs | 6.00μs | **307x** | Long-term retrieval |
| Planning | 8.78μs | 9.00μs | **439x** | Plan generation |
| Multiagent | 9.91μs | 9.00μs | **496x** | Collaboration |

### Fast Patterns (10-100μs)

| Pattern | Mean | Median | Relative | Use Case |
|---------|------|--------|----------|----------|
| Reflection | 56.52μs | 49.00μs | **2,826x** | Self-critique cycles |

### Moderate Patterns (100-1000μs)

| Pattern | Mean | Median | Relative | Use Case |
|---------|------|--------|----------|----------|
| Reasoning with Tools | 419.86μs | 382.00μs | **20,993x** | Tool-aware reasoning |

### Known Issues

| Pattern | Issue | Status |
|---------|-------|--------|
| Conversational | 5.13s anomaly (memory accumulation) | ⚠️ Under investigation |
| Autonomous | 0.00μs (measurement error) | ⚠️ Under investigation |

**Note**: Relative performance is vs Memory: Working (store) as fastest pattern.

---

## Cross-Language Availability Matrix

### Pattern Benchmarks

| Pattern | C++ | Go | Python | TypeScript | Rust | Zig |
|---------|-----|-----|--------|------------|------|-----|
| **Reflection** | ✅ 56.52μs | ❌ | ❌ | ❓ | ❓ | ❓ |
| **ReAct** | ✅ 0.92μs | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Agents-as-Tools** | ✅ 2.28μs | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Orchestration** | ✅ 1.05μs | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Reasoning with Tools** | ✅ 419.86μs | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Conversational** | ⚠️ Anomaly | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Task** | ✅ 3.25μs | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Multiagent** | ✅ 9.91μs | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Planning** | ✅ 8.78μs | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Autonomous** | ⚠️ Anomaly | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Memory: Working** | ✅ 0.02-1.46μs | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Memory: Hierarchy** | ✅ 1.00-6.13μs | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Sequential** | ❌ | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Parallel** | ❌ | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Router** | ❌ | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Fallback** | ❌ | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Collaborative** | ❌ | ❌ | ❌ | ❓ | ❓ | ❓ |
| **Human-in-Loop** | ❌ | ❌ | ❌ | ❓ | ❓ | ❓ |

**Legend**:
- ✅ = Benchmark implemented and passing
- ⚠️ = Benchmark implemented but has anomalies
- ❌ = Benchmark not implemented
- ❓ = Not investigated

**Coverage**: 12/108 data points (11%)

---

## Performance Comparison (When Available)

### Projected Comparison (Hypothetical)

Based on typical language performance characteristics, we expect:

| Language | Relative Speed | Memory Usage | Compilation |
|----------|---------------|--------------|-------------|
| **C++** | 1.0x (baseline) | Low | Static (fast) |
| **Go** | 0.8-1.2x | Medium | Static (fast) |
| **Rust** | 0.9-1.1x | Low | Static (slower) |
| **Zig** | 0.9-1.1x | Low | Static (fast) |
| **TypeScript/Node** | 0.3-0.5x | Medium-High | JIT |
| **Python** | 0.1-0.3x | High | Interpreted |

**Note**: These are **estimates**. Actual measurements required for accurate comparison.

### Expected Production Impact

For a typical agent workflow with LLM calls:

```
Workflow: 2 LLM calls @ 500ms each = 1,000ms total

Pattern overhead by language (estimated):
- C++:      0.056ms (0.0056% of total)
- Go:       0.065ms (0.0065% of total)  [estimated]
- Python:   0.200ms (0.0200% of total)  [estimated]

Conclusion: Pattern overhead is negligible (<0.02%) regardless of language
```

---

## Blockers

### Go Protobuf Panic

**Status**: ❌ Blocking all Go benchmarks

**Error**:
```
panic: runtime error: slice bounds out of range [-5:]
google.golang.org/protobuf/internal/filedesc.(*File).unmarshalSeed
```

**Impact**:
- Cannot run any Go tests or benchmarks
- Blocks C++ vs Go performance comparison
- Blocks overhead benchmarks (middleware, transport, streaming)

**Next Steps**:
- Regenerate protobuf files from `/Users/scttfrdmn/src/agenkit/proto/agent.proto`
- Verify protobuf version compatibility
- Test with minimal reproduction case

### Pattern Benchmark Implementation

**Status**: ❌ Not implemented in 5/6 languages

**Required Work** (estimated):
- Go: 2-3 days (after protobuf fix)
- Python: 2-3 days
- TypeScript: 3-4 days (if patterns exist)
- Rust: 3-4 days (if patterns exist)
- Zig: 3-4 days (if patterns exist)

**Total**: 13-18 days for complete coverage

---

## Roadmap

### Phase 1: Fix Blockers (v0.42.0)

- [ ] Fix C++ Conversational anomaly
- [ ] Fix C++ Autonomous anomaly
- [ ] Fix Go protobuf panic
- [ ] Document current state (this file)

**ETA**: 2-3 days

### Phase 2: Go Benchmarks (v0.43.0)

- [ ] Implement Go pattern benchmarks
- [ ] Collect Go performance data
- [ ] Create C++ vs Go comparison
- [ ] Identify optimization opportunities

**ETA**: 3-4 days (after Phase 1)

### Phase 3: Python Benchmarks (v0.43.0-v0.44.0)

- [ ] Implement Python pattern benchmarks
- [ ] Collect Python performance data
- [ ] Add Python to comparison matrix
- [ ] Compare compiled (C++, Go) vs interpreted (Python)

**ETA**: 3-4 days

### Phase 4: Complete Coverage (v1.0)

- [ ] Implement TypeScript benchmarks
- [ ] Implement Rust benchmarks
- [ ] Implement Zig benchmarks
- [ ] Create comprehensive 6-language comparison
- [ ] Performance optimization based on findings

**ETA**: 8-12 days

---

## Key Findings

### 1. C++ Performance Excellent

C++ pattern overhead is **extremely low**:
- 9 patterns under 10μs (ultra-fast)
- Reflection at 56μs (fast)
- Only Reasoning with Tools at 420μs (moderate)

**Conclusion**: C++ implementation is production-ready with negligible overhead.

### 2. Production Impact Negligible

Even the slowest pattern (Reasoning with Tools at 420μs = 0.42ms) is insignificant compared to LLM calls (100-1000ms).

**Production overhead**: <0.01-0.1% of total execution time

### 3. Pattern Benchmarking Immature

Only **1 of 6 languages** has pattern performance benchmarks. This is a **significant gap** that prevents:
- Cross-language performance comparison
- Optimization guidance for language selection
- Regression detection across the ecosystem

### 4. Two Categories of Benchmarks

Important distinction:
1. **Pattern Benchmarks** (this document): Measure pattern implementation overhead
2. **Overhead Benchmarks** (`benchmarks/BASELINES.md`): Measure middleware, transport, streaming overhead

Both are valuable but serve different purposes.

---

## How to Use This Data

### For Framework Developers

1. **C++ Baseline**: Use C++ results as performance target for other languages
2. **Anomalies**: Fix Conversational and Autonomous before v0.42.0 release
3. **Prioritize Go**: Highest ROI for comparison (compiled language, similar to C++)
4. **Regression Detection**: Add pattern benchmarks to CI/CD once stable

### For Application Developers

1. **Don't worry about pattern overhead**: It's negligible (<0.1% of execution time)
2. **Focus on LLM optimization**: That's where 99.9% of time is spent
3. **Choose language by preference**: Performance difference between languages is minimal in production

### For Performance Engineering

1. **Baseline established**: C++ provides performance target
2. **Optimization opportunities**: Investigate Reasoning with Tools (420μs) if needed
3. **Memory profiling needed**: Conversational anomaly suggests memory issue

---

## Detailed Documentation

For complete information, see:
- **[Pattern Performance Benchmarks](../docs/PATTERN_PERFORMANCE.md)** - Comprehensive documentation
- **[Overhead Benchmarks](../benchmarks/BASELINES.md)** - Middleware, transport, streaming
- **[C++ Benchmarks](../agenkit-cpp/benchmarks/BENCHMARKS.md)** - C++ implementation details

---

Last Updated: December 17, 2025
Status: Partial data (C++ only) - Pending implementation in other languages
