# CI Benchmark Integration

This document describes how continuous integration (CI) benchmarks work in agenkit and how to use them effectively.

## Overview

The agenkit project uses automated benchmark regression detection in CI to prevent performance degradations from being merged. Benchmarks run automatically on pull requests and compare results against the base branch.

## Workflow

### When Benchmarks Run

Benchmarks automatically run on:
- **Pull Requests** to `main` or `develop` branches
- **Push to main** (for baseline updates)
- **Manual triggers** via GitHub Actions UI

Benchmarks only run when relevant files change:
- `agenkit/**` - Python implementation
- `agenkit-go/**` - Go implementation
- `benchmarks/**` - Benchmark files
- `.github/workflows/benchmarks.yml` - CI config

### What Gets Benchmarked

#### Go Benchmarks
All benchmarks in `agenkit-go/benchmarks/`:
- Middleware overhead (retry, metrics, circuit breaker, rate limiter, timeout, batching)
- Transport protocols (HTTP/1.1, HTTP/2, HTTP/3)
- Streaming vs batch performance
- Memory allocation analysis

**Run time**: ~10-15 minutes (5 iterations per benchmark)

#### Python Benchmarks
Selected benchmarks from `benchmarks/`:
- Middleware overhead summary
- HTTP/1.1 latency baseline
- HTTP/1.1 streaming (10 chunks)

**Run time**: ~3-5 minutes (optimized for CI speed)

**Note**: Full Python benchmark suite can be run locally (see [BASELINES.md](./BASELINES.md))

## Reading Benchmark Reports

### PR Comments

When benchmarks complete, a comment is automatically posted to your PR with results:

```markdown
# 📊 Benchmark Results

## Go Benchmarks
<details>
<summary>Click to view detailed Go benchmark comparison</summary>

name           old time/op    new time/op    delta
RetryMW-12       5.21µs ± 2%    5.18µs ± 1%    ~
MetricsMW-12     8.45µs ± 3%    8.52µs ± 2%  +0.83%
...
```

### Interpreting Results

#### Performance Changes
- **Negative % = Improvement** (faster): `-5.0%` means 5% faster ✅
- **Positive % = Regression** (slower): `+10.0%` means 10% slower ⚠️
- **`~` = No significant change**: Difference within statistical noise

#### Regression Thresholds

| Category | Warning Threshold | Action |
|----------|------------------|--------|
| Middleware | >15% regression | Review carefully |
| Transport | >20% regression | Review carefully |
| Streaming | >20% regression | Review carefully |
| Memory | >25% increase | Review carefully |

**Why different thresholds?**
- Middleware patterns have low variance, so smaller regressions are meaningful
- Transport/streaming benchmarks have more variance due to network simulation
- Memory allocations can vary more due to GC timing

### Example Interpretations

✅ **Good**:
```
RetryMiddleware-12    5.21µs ± 2%    5.18µs ± 1%   -0.58%
```
Minor improvement, within noise. No action needed.

✅ **Good**:
```
HTTP1Latency-12      54.9µs ± 5%    53.2µs ± 4%   -3.10%
```
Clear improvement. Great work!

⚠️ **Review**:
```
StreamingVsBatch-12   147µs ± 3%     178µs ± 4%  +21.09%
```
Significant regression (>20%). Please investigate:
1. What changed in streaming logic?
2. Is this an acceptable trade-off?
3. Can it be optimized?

❌ **Fix Required**:
```
MetricsMiddleware-12  8.45µs ± 2%   12.31µs ± 3%  +45.68%
```
Major regression (>45%). This needs to be fixed before merging:
1. Profile the code to find the bottleneck
2. Optimize or revert the change
3. Re-run benchmarks to verify fix

## Benchstat Output Fields

### Time Metrics
- **old time/op**: Baseline performance (base branch)
- **new time/op**: Current performance (PR branch)
- **delta**: Percentage change

### Memory Metrics
- **old alloc/op**: Baseline memory allocated per operation
- **new alloc/op**: Current memory allocated per operation
- **delta**: Percentage change in allocations

### Allocation Metrics
- **old allocs/op**: Baseline number of allocations
- **new allocs/op**: Current number of allocations
- **delta**: Percentage change

### Statistical Significance
- **±X%**: Confidence interval (standard deviation)
- **~**: Statistically insignificant change (overlapping confidence intervals)

## Local Benchmark Comparison

You can run the same comparison locally before pushing:

### Go Benchmarks

```bash
# 1. Run benchmarks on your feature branch
cd agenkit-go/benchmarks
go test -bench=. -benchmem -count=5 > /tmp/new.txt

# 2. Switch to base branch
git checkout main
go test -bench=. -benchmem -count=5 > /tmp/old.txt

# 3. Compare with benchstat
go install golang.org/x/perf/cmd/benchstat@latest
benchstat /tmp/old.txt /tmp/new.txt
```

### Python Benchmarks

```bash
# 1. Run benchmarks on your feature branch
source venv/bin/activate
pytest benchmarks/test_middleware_overhead.py::test_middleware_benchmark_summary -v -s

# 2. Note the results, then switch branches
git checkout main
pytest benchmarks/test_middleware_overhead.py::test_middleware_benchmark_summary -v -s

# 3. Compare manually (or use pytest-benchmark for JSON comparison)
```

## Troubleshooting

### False Positives

Benchmarks can show variance due to:
- **System load**: Other processes running
- **Thermal throttling**: CPU temperature affecting clock speed
- **Memory pressure**: OS swapping/paging
- **Network latency**: For transport benchmarks

**Solutions**:
1. Re-run the benchmark workflow (GitHub UI > Actions > Re-run jobs)
2. Run locally on a quiet system
3. Increase `-count` iterations (reduces noise but takes longer)

### Benchmark Failures

If benchmarks fail to run:

1. **Timeout**: Increase timeout in workflow (currently 30m)
2. **Out of memory**: Reduce concurrent benchmark iterations
3. **Compilation error**: Fix the code and push again
4. **Test panics**: Check for race conditions or nil pointers

### Skipping Benchmarks

To skip benchmarks on a PR (not recommended):
- Add `[skip benchmarks]` to your commit message
- Only use for documentation-only changes

## Best Practices

### Before Submitting PR

1. **Run benchmarks locally** to catch obvious regressions
2. **Profile your code** if you're changing hot paths
3. **Consider trade-offs** if performance decreases for other benefits
4. **Document intentional regressions** in PR description

### During PR Review

1. **Review benchmark results** as part of code review
2. **Question unexpected changes** even if within thresholds
3. **Ask for optimization** if regressions are unacceptable
4. **Approve if acceptable** with clear justification

### After Merging

1. **Monitor baselines** over time (artifacts stored for 30 days)
2. **Update BASELINES.md** if intentional performance changes occur
3. **Track trends** across multiple PRs for gradual regressions

## CI Configuration

### Modifying the Workflow

Edit `.github/workflows/benchmarks.yml` to:
- Change benchmark iteration count (`-count=5`)
- Add/remove specific benchmarks
- Adjust timeout limits
- Modify regression thresholds

### Adding New Benchmarks

1. Create benchmark in `benchmarks/` or `agenkit-go/benchmarks/`
2. Follow existing naming conventions (`Benchmark*` for Go, `test_*` for Python)
3. Ensure benchmark completes in reasonable time (<2 minutes)
4. Add to workflow if it should run on every PR

### Baseline Storage

**Current approach** (v1):
- Baselines are computed dynamically from base branch
- No persistent storage (fetches and runs on each PR)

**Future improvement** (v2):
- Store baseline results as artifacts
- Compare against stored baselines (faster)
- Track historical trends over time

## Performance Dashboard (Future)

Future plans include:
- Web dashboard for visualizing benchmark trends
- Historical performance graphs
- Comparison across Git branches/tags
- Regression detection with alerts

## Questions?

- 💬 Discussions: [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)
- 🐛 Issues: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
- 📧 Email: [your-email]

---

Last updated: November 11, 2025
