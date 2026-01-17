# Test Parity Dashboard

**Last Updated:** 2026-01-17 20:20:14 UTC
**Status:** Tracking test parity across 6 language implementations

## Overview

This dashboard tracks test coverage across all Agenkit language implementations to ensure feature parity and quality consistency.

## Test Count Summary

| Language | Total Tests | vs Python | Parity % | Status |
|----------|------------|-----------|----------|--------|
| **Python** | 1836 | — | 100% | ✅ Reference |
| **Go** | 950 | -886 | 51.7% | 🟡 Fair |
| **C++** | 793 suites | —¹ | 647.8% | ✅ Excellent |
| **Rust** | 681 | -1155 | 37.0% | 🟠 Poor |
| **Zig** | 214 | -1622 | 11.6% | 🔴 Critical |
| **TypeScript** | 464² | —² | 25.2% | 🟠 Poor |

¹ C++ reports test suites not individual tests. Estimated ≈15 tests/suite = 11895 total tests.
² TypeScript count may be estimated from test files.


## Category Breakdown

### Core Categories (Critical for Production)

| Category | Python | Go | C++ | Rust | Zig | TypeScript |
|----------|--------|-----|-----|------|-----|------------|
| **Patterns** | 439 | 362 ✅ | 310 ✅ | 133 ✅ | — | 7 |
| **Techniques** | 240 | 37 ❌ | 22 ❌ | 0 ❌ | — | 0 ❌ |
| **Safety** | 162 | 94 ❌ | 0 ❌ | 52 ❌ | — | 0 ❌ |
| **Adapters** | 151 | 54 ⚠️ | ~8 ❌ | 31 ❌ | — | 0 ❌ |
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
| Go | 950 | 1,500 | +550 | Techniques, Safety, Routing, Chaos |
| C++ | 793 | 1,500 | +-10395 | Techniques, Safety, Adapters |
| Rust | 681 | 1,500 | +819 | Techniques, Safety, Adapters |
| Zig | 214 | 1,000 | +786 | Evaluation, Techniques |
| TypeScript | 464 | 1,200 | +736 | Techniques, Safety, Adapters |

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
