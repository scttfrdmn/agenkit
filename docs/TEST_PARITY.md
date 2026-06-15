# Test Parity Dashboard

**Last Updated:** 2026-06-14 22:51:06 UTC
**Status:** Tracking test parity across 6 language implementations

## Overview

This dashboard tracks test coverage across all Agenkit language implementations to ensure feature parity and quality consistency.

## Test Count Summary

| Language | Total Tests | vs Python | Parity % | Status |
|----------|------------|-----------|----------|--------|
| **Python** | 2044 | — | 100% | ✅ Reference |
| **Go** | 1244 | -800 | 60.8% | 🟢 Good |
| **C++** | 1034 suites | —¹ | 758.8% | ✅ Excellent |
| **Rust** | 1253 | -791 | 61.3% | 🟢 Good |
| **Zig** | 214 | -1830 | 10.4% | 🔴 Critical |
| **TypeScript** | 928² | —² | 45.4% | 🟡 Fair |

¹ C++ reports test suites not individual tests. Estimated ≈15 tests/suite = 15510 total tests.
² TypeScript count may be estimated from test files.


## Category Breakdown

### Core Categories (Critical for Production)

| Category | Python | Go | C++ | Rust | Zig | TypeScript |
|----------|--------|-----|-----|------|-----|------------|
| **Patterns** | 443 | 362 ✅ | 310 ✅ | 133 ✅ | — | 16 |
| **Techniques** | 240 | 107 ❌ | 116 ❌ | 95 ❌ | — | 216 ❌ |
| **Safety** | 162 | 94 ❌ | 0 ❌ | 60 ❌ | — | 135 ⚠️ |
| **Adapters** | 141 | 89 ⚠️ | ~8 ❌ | 48 ❌ | — | 0 ❌ |
| **Evaluation** | 116 | 127 ⚠️ | — | 73 ⚠️ | — | 0 ❌ |
| **Middleware** | 92 | 91 ⚠️ | — | — | — | — |

**Legend:** ✅ Good parity (>80%) | ⚠️ Partial (40-80%) | ❌ Missing (<40%) | — Not counted

### Advanced Categories (Nice to Have)

| Category | Python | Go | C++ | Rust | Zig | TypeScript |
|----------|--------|-----|-----|------|-----|------------|
| **Routing** | 34 | 0 | — | — | — | — |
| **Chaos** | 53 | 0 | — | — | — | — |
| **Property** | 37 | 0 | 0 | 0 | — | 0 |
| **Budget** | 51 | ✅ | — | — | — | — |
| **Memory** | 101 | 18 | — | — | — | — |


## Active Parity Issues

Track progress on test parity implementation:

### High Priority (Critical Path)
- [#349](https://github.com/scttfrdmn/agenkit/issues/349) - Go: Implement comprehensive techniques module tests
- [#350](https://github.com/scttfrdmn/agenkit/issues/350) - C++: Implement comprehensive techniques module tests
- [#351](https://github.com/scttfrdmn/agenkit/issues/351) - Rust: Implement comprehensive techniques module tests
- [#352](https://github.com/scttfrdmn/agenkit/issues/352) - C++: Implement comprehensive safety module tests
- [#353](https://github.com/scttfrdmn/agenkit/issues/353) - Rust: Implement comprehensive safety module tests
- [#354](https://github.com/scttfrdmn/agenkit/issues/354) - TypeScript: Implement comprehensive techniques module tests
- [#355](https://github.com/scttfrdmn/agenkit/issues/355) - Rust: Implement comprehensive adapter tests
- [#356](https://github.com/scttfrdmn/agenkit/issues/356) - C++: Implement comprehensive adapter tests

### Medium Priority
- [#357](https://github.com/scttfrdmn/agenkit/issues/357) - Zig: Implement evaluation framework tests
- [#358](https://github.com/scttfrdmn/agenkit/issues/358) - Go: Implement routing module tests
- [#359](https://github.com/scttfrdmn/agenkit/issues/359) - Go: Implement chaos engineering tests

### Cross-Cutting
- [#360](https://github.com/scttfrdmn/agenkit/issues/360) - Cross-Language: Implement property-based testing framework
- [#361](https://github.com/scttfrdmn/agenkit/issues/361) - All Languages: Test parity tracking and dashboard ✅

## Parity Goals

Target test counts for "meaningful parity" (85% of Python's comprehensive coverage):

| Language | Current | Target | Gap | Priority Work |
|----------|---------|--------|-----|---------------|
| Go | 1244 | 1,500 | +256 | Techniques, Safety, Routing, Chaos |
| C++ | 1034 | 1,500 | +-14010 | Techniques, Safety, Adapters |
| Rust | 1253 | 1,500 | +247 | Techniques, Safety, Adapters |
| Zig | 214 | 1,000 | +786 | Evaluation, Techniques |
| TypeScript | 928 | 1,200 | +272 | Techniques, Safety, Adapters |

## Methodology

### Test Counting

**Python:** `pytest --collect-only` counts individual test functions
**Go:** `go test -v` counts test runs (subtests counted separately)
**C++:** `ctest` counts test suites/executables (each contains multiple tests)
**Rust:** `cargo test` counts test functions
**Zig:** `zig build test` counts inline test blocks
**TypeScript:** `npm test` counts Jest test cases

### Parity Calculation

Parity % = (Language Tests / Python Tests) × 100

For C++, we estimate ~15 tests per suite based on existing pattern tests.

### Update Frequency

This dashboard auto-updates on every commit via CI and can be manually regenerated with:

```bash
./scripts/test-parity.sh
```

## Notes

- **Pattern Parity**: All languages have 100% pattern parity (18 patterns implemented)
- **Core Features**: Focus on techniques, safety, and adapters (highest ROI)
- **Language-Specific**: Some categories don't apply to all languages (e.g., WASM)
- **Test Granularity**: Different languages have different test granularities

---

**Raw Data:** [`test-parity-report.json`](../test-parity-report.json)
