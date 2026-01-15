# Test Parity Tracking System

This document explains the test parity tracking system for the Agenkit project.

## Overview

The test parity system ensures that all 6 language implementations (Python, Go, C++, Rust, Zig, TypeScript) maintain consistent test coverage across core features.

## Components

### 1. Test Parity Script (`scripts/test-parity.sh`)

Automated script that:
- Runs all test suites across 6 languages
- Extracts test counts per category per language
- Generates JSON report (`test-parity-report.json`)
- Generates markdown dashboard (`docs/TEST_PARITY.md`)
- Calculates parity percentages

**Usage:**
```bash
./scripts/test-parity.sh
```

**Output:**
- `test-parity-report.json` - Machine-readable test counts
- `docs/TEST_PARITY.md` - Human-readable dashboard

### 2. Test Parity Dashboard (`docs/TEST_PARITY.md`)

Interactive dashboard showing:
- Current test counts by language
- Parity percentages vs Python (reference implementation)
- Category breakdowns (patterns, techniques, safety, etc.)
- Links to GitHub issues for test gaps
- Parity goals and progress tracking

**View:** [docs/TEST_PARITY.md](docs/TEST_PARITY.md)

### 3. Parity Validation Tests (`tests/test_parity_validation.py`)

Automated pytest suite that validates parity thresholds:
- **Minimum Parity Enforcement:** Fails CI if any language drops below threshold
- **Category Validation:** Checks category-specific parity (patterns, safety, etc.)
- **Regression Detection:** Prevents test count decreases
- **Quality Checks:** Validates report structure and data integrity

**Thresholds:**
- Go: 50% (currently 53.0%)
- C++: 40% (currently 44.3%)
- Rust: 15% (currently 15.4%)
- TypeScript: 18% (currently 18.3%)
- Zig: 13% (currently 13.7%)

**Usage:**
```bash
# Run validation tests
uv run pytest tests/test_parity_validation.py -v

# Run just threshold checks
uv run pytest tests/test_parity_validation.py -k threshold -v
```

### 4. CI Integration (`.github/workflows/test-parity.yml`)

Automated CI workflow that:
- Runs on every push to main
- Runs on every pull request
- Runs daily at 00:00 UTC
- Generates parity report with `test-parity.sh`
- **Validates thresholds with pytest suite** (NEW in v0.48.0)
- Posts parity report as PR comment
- Auto-commits updated dashboard to main branch
- Detects and alerts on parity regressions
- **Fails CI if thresholds violated** (NEW in v0.48.0)

## Parity Goals

### Target Parity Levels

| Priority | Parity % | Status | Description |
|----------|----------|--------|-------------|
| **Critical** | ≥80% | ✅ | Excellent parity - production ready |
| **Good** | 60-80% | 🟢 | Good parity - minor gaps |
| **Fair** | 40-60% | 🟡 | Fair parity - significant work needed |
| **Poor** | 20-40% | 🟠 | Poor parity - major gaps |
| **Critical Gap** | <20% | 🔴 | Critical gaps - not production ready |

### Language Targets

| Language | Current | Target | Gap | Priority Work |
|----------|---------|--------|-----|---------------|
| **Python** | 1,789 | — | — | Reference implementation |
| **Go** | 926 | 1,500 | +574 | Techniques, Routing, Chaos |
| **C++** | 598* | 1,500 | +902 | Techniques, Safety, Adapters |
| **Rust** | 277 | 1,500 | +1,223 | Techniques, Safety, Adapters |
| **Zig** | 214 | 1,000 | +786 | Evaluation, Techniques |
| **TypeScript** | 328 | 1,200 | +872 | Techniques, Safety, Adapters |

\* C++ reports test suites (≈15 tests/suite)

## Test Categories

### Core Categories (Critical for Production)

1. **Patterns** (✅ Full parity) - 18 agent patterns
2. **Techniques** (❌ Major gap) - Reasoning, compositions, protocols
3. **Safety** (❌ Major gap) - Rate limiting, circuit breakers, validation
4. **Adapters** (⚠️ Partial) - LLM providers, transports
5. **Evaluation** (⚠️ Partial) - Benchmarks, metrics, optimization
6. **Middleware** (⚠️ Partial) - Timeout, retry, observability

### Advanced Categories (Nice to Have)

7. **Routing** - Semantic routing, load balancing
8. **Chaos** - Chaos engineering tests
9. **Property** - Property-based testing
10. **Budget** - Token/cost management
11. **Memory** - Memory backends

## How to Improve Parity

### For Contributors

1. **Check the dashboard:** Review [docs/TEST_PARITY.md](docs/TEST_PARITY.md)
2. **Pick an issue:** Choose from [test parity issues](https://github.com/scttfrdmn/agenkit/labels/test-parity)
3. **Reference Python:** Use Python tests as the source of truth
4. **Match behavior:** Ensure tests verify equivalent behavior
5. **Run parity script:** Verify improvement with `./scripts/test-parity.sh`
6. **Submit PR:** Include test parity impact in PR description

### For Maintainers

1. **Review parity reports:** Check automated PR comments
2. **Monitor regressions:** CI will alert if tests decrease
3. **Track progress:** Dashboard auto-updates on main branch
4. **Close issues:** Issues auto-close when parity goals met
5. **Set priorities:** Focus on critical gaps first

## Interpreting Parity Reports

### Understanding Test Counts

Different languages count tests differently:

- **Python:** Individual test functions (pytest)
- **Go:** Test runs including subtests (go test)
- **C++:** Test suites/executables (ctest) - each contains ~15 tests
- **Rust:** Test functions (cargo test)
- **Zig:** Inline test blocks (zig build test)
- **TypeScript:** Jest test cases (npm test)

### Parity Calculation

```
Parity % = (Language Tests / Python Tests) × 100
```

For C++, we estimate actual test count by multiplying suites × 15.

### Status Indicators

- ✅ **Green** - Good parity (>80%)
- 🟡 **Yellow** - Fair parity (40-80%)
- 🔴 **Red** - Critical gap (<40%)
- ⚠️ **Warning** - Partial coverage (40-80%)
- — **N/A** - Not applicable or not counted

## FAQ

**Q: Why is Python the reference?**
A: Python is the first and most mature implementation with comprehensive test coverage.

**Q: Do all languages need identical test counts?**
A: No. The goal is "meaningful parity" - equivalent behavior testing, not identical test counts.

**Q: What if a language can't implement a feature?**
A: Mark as "N/A" in the dashboard. Some features are language-specific (e.g., WASM).

**Q: How often does the dashboard update?**
A: Automatically on every commit to main, on PRs, and daily at 00:00 UTC.

**Q: Can I run the parity script locally?**
A: Yes! `./scripts/test-parity.sh` - requires all 6 language toolchains installed.

**Q: What's the priority for closing gaps?**
A: 1) Patterns (✅ done), 2) Techniques, 3) Safety, 4) Adapters, 5) Everything else.

## Related Issues

- [#349](https://github.com/scttfrdmn/agenkit/issues/349) - Go techniques
- [#350](https://github.com/scttfrdmn/agenkit/issues/350) - C++ techniques
- [#351](https://github.com/scttfrdmn/agenkit/issues/351) - Rust techniques
- [#352](https://github.com/scttfrdmn/agenkit/issues/352) - C++ safety
- [#353](https://github.com/scttfrdmn/agenkit/issues/353) - Rust safety
- [#354](https://github.com/scttfrdmn/agenkit/issues/354) - TypeScript techniques
- [#355](https://github.com/scttfrdmn/agenkit/issues/355) - Rust adapters
- [#356](https://github.com/scttfrdmn/agenkit/issues/356) - C++ adapters
- [#357](https://github.com/scttfrdmn/agenkit/issues/357) - Zig evaluation
- [#358](https://github.com/scttfrdmn/agenkit/issues/358) - Go routing
- [#359](https://github.com/scttfrdmn/agenkit/issues/359) - Go chaos
- [#360](https://github.com/scttfrdmn/agenkit/issues/360) - Property testing
- [#361](https://github.com/scttfrdmn/agenkit/issues/361) - Tracking dashboard (this)

## Contact

Questions? Open an issue or discussion on GitHub.
