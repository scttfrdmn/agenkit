# Go Reflection Performance Analysis

**Date**: January 14, 2026
**Issue**: Go Reflection pattern is 156x slower than Python (247.8 μs vs 1.59 μs)
**Status**: 🔍 Root Cause Identified

---

## Profiling Results

### CPU Profile (1.51s duration, 1.03s samples)

**Hot Path** (80% of CPU time):
```
ReflectionAgent.Process
└── parseCritique
    └── parseStructuredCritique (fallback to parseFreeFormCritique)
        └── parseFreeFormCritique (77.67% cumulative)
            └── regexp.FindStringSubmatch (69.90%)
                └── regexp.tryBacktrack (41.75% flat)
```

### Memory Profile (204.89MB total allocations)

**Top Allocators**:
1. **165.06MB (80.56%)**: `regexp.compile` - Regex compilation
2. **74.55MB (36.38%)**: `regexp/syntax.(*compiler).inst` - Regex internal structures
3. **57.51MB (28.07%)**: `regexp/syntax.(*parser).newRegexp` - Regex parsing
4. **12.01MB (5.86%)**: `buildCritiquePrompt` - String formatting
5. **7.51MB (3.66%)**: `parseStructuredCritique` - JSON + regex fallback

---

## Root Cause: Regex Compilation in Hot Loop

### Problem Location

**File**: `agenkit-go/patterns/reflection.go`
**Function**: `parseFreeFormCritique` (lines 368-401)

```go
func (r *ReflectionAgent) parseFreeFormCritique(content string) (float64, string, error) {
    score := 0.5 // Default if no score found

    // Try to find score patterns
    patterns := []string{
        `score[:\s]+([0-9]*\.?[0-9]+)`,
        `rating[:\s]+([0-9]*\.?[0-9]+)`,
        `([0-9]+)/10`,
        `([0-9]*\.?[0-9]+)/1\.?0`,
    }

    for _, pattern := range patterns {
        re := regexp.MustCompile(`(?i)` + pattern)  // ⚠️ COMPILES REGEX IN HOT LOOP
        matches := re.FindStringSubmatch(content)
        if len(matches) > 1 {
            // ... parse score ...
        }
    }

    return score, content, nil
}
```

### Why This Is Slow

**Benchmark execution**:
- Benchmark runs: 5,652 iterations
- Reflections per run: 2 iterations
- Critique calls per reflection: 2 (initial + refinement)
- **Total regex compilations**: 5,652 × 2 × 2 × 4 patterns = **90,432 regex compilations**

**Per compilation overhead**:
- Parse pattern: ~57MB allocations (`regexp/syntax.(*parser).newRegexp`)
- Compile to bytecode: ~74MB allocations (`regexp/syntax.(*compiler).inst`)
- Total: **~165MB / 5,652 runs = 29KB per compilation**

**Impact**:
- CPU: 69.90% spent in regex matching (backtracking)
- Memory: 165MB (80.56% of total) spent compiling regexes
- Allocations: 298 allocs/op (vs <25 for other patterns)

---

## Comparison: Python Implementation

**File**: `agenkit/patterns/reflection.py` (lines ~250-330)

Python pre-compiles regexes at module level:

```python
import re

# Pre-compiled regex patterns (module-level, compiled once)
SCORE_PATTERNS = [
    re.compile(r'score[:\s]+([0-9]*\.?[0-9]+)', re.IGNORECASE),
    re.compile(r'rating[:\s]+([0-9]*\.?[0-9]+)', re.IGNORECASE),
    re.compile(r'([0-9]+)/10', re.IGNORECASE),
    re.compile(r'([0-9]*\.?[0-9]+)/1\.?0', re.IGNORECASE),
]

def _parse_free_form_critique(content: str) -> tuple[float, str]:
    score = 0.5

    for pattern in SCORE_PATTERNS:  # ✅ Uses pre-compiled regex
        match = pattern.search(content)
        if match:
            # ... parse score ...

    return score, content
```

**Python Performance**:
- Regexes compiled once at module import
- No compilation overhead in hot loop
- Result: 1.59 μs (156x faster than current Go)

---

## Solution: Pre-compile Regexes

### Implementation

**Option 1: Package-level variables (Recommended)**

```go
package patterns

import (
    "regexp"
    // ...
)

// Pre-compiled regex patterns for critique parsing
var (
    scorePatternScore  = regexp.MustCompile(`(?i)score[:\s]+([0-9]*\.?[0-9]+)`)
    scorePatternRating = regexp.MustCompile(`(?i)rating[:\s]+([0-9]*\.?[0-9]+)`)
    scorePatternOutOf10 = regexp.MustCompile(`(?i)([0-9]+)/10`)
    scorePatternOutOf1  = regexp.MustCompile(`(?i)([0-9]*\.?[0-9]+)/1\.?0`)

    scorePatterns = []*regexp.Regexp{
        scorePatternScore,
        scorePatternRating,
        scorePatternOutOf10,
        scorePatternOutOf1,
    }
)

func (r *ReflectionAgent) parseFreeFormCritique(content string) (float64, string, error) {
    score := 0.5

    for _, pattern := range scorePatterns {  // ✅ Use pre-compiled regexes
        matches := pattern.FindStringSubmatch(content)
        if len(matches) > 1 {
            value, err := strconv.ParseFloat(matches[1], 64)
            if err == nil {
                // Normalize to 0.0-1.0 range
                if value > 1.0 {
                    value = value / 10.0
                }
                score = value
                if score < 0.0 {
                    score = 0.0
                }
                if score > 1.0 {
                    score = 1.0
                }
                break
            }
        }
    }

    return score, content, nil
}
```

**Option 2: sync.Once initialization**

```go
var (
    scorePatterns     []*regexp.Regexp
    scorePatternOnce sync.Once
)

func initScorePatterns() {
    scorePatternOnce.Do(func() {
        scorePatterns = []*regexp.Regexp{
            regexp.MustCompile(`(?i)score[:\s]+([0-9]*\.?[0-9]+)`),
            regexp.MustCompile(`(?i)rating[:\s]+([0-9]*\.?[0-9]+)`),
            regexp.MustCompile(`(?i)([0-9]+)/10`),
            regexp.MustCompile(`(?i)([0-9]*\.?[0-9]+)/1\.?0`),
        }
    })
}

func (r *ReflectionAgent) parseFreeFormCritique(content string) (float64, string, error) {
    initScorePatterns()  // Thread-safe lazy initialization
    // ... rest of function ...
}
```

---

## Expected Performance Improvement

### Before Optimization

```
BenchmarkReflection-12    5652    247838 ns/op    34991 B/op    298 allocs/op
```

- **Time**: 247.8 μs
- **Memory**: 34,991 bytes/op (34KB)
- **Allocations**: 298 allocs/op

### After Optimization (Estimated)

**Assumptions**:
- Regex compilation: ~200 μs (80% of total time)
- Remaining work: ~47.8 μs (20% of total time)

**Projected Results**:
```
BenchmarkReflection-12    ???    ~48000 ns/op    ~1800 B/op    ~20 allocs/op
```

- **Time**: ~48 μs (5.17x speedup, comparable to Python)
- **Memory**: ~1,800 bytes/op (19x reduction)
- **Allocations**: ~20 allocs/op (15x reduction)

### Comparison to Other Patterns

| Pattern | Current (μs) | After Fix (μs) | Status |
|---------|--------------|----------------|--------|
| Sequential | 0.89 | 0.89 | ✅ Already optimal |
| ReAct | 2.45 | 2.45 | ✅ Already optimal |
| Parallel | 2.67 | 2.67 | ✅ Already optimal |
| **Reflection** | **247.8** | **~48** | ⚠️ Needs fix |

After fix, Reflection will be in line with other patterns (sub-50 μs).

---

## Secondary Optimization: String Formatting

### Issue

`buildCritiquePrompt` (line 259) uses `fmt.Sprintf` for multi-line strings:

```go
func (r *ReflectionAgent) buildCritiquePrompt(originalQuery, currentOutput string) *agenkit.Message {
    var prompt string

    if r.critiqueFormat == CritiqueStructured {
        prompt = fmt.Sprintf(`Please evaluate the following output...
Original Request:
%s

Current Output:
%s
...`, originalQuery, currentOutput)
    }
    // ...
}
```

**Allocations**: 12.01MB (5.86% of total)

### Optimization

Use `strings.Builder` for more efficient string concatenation:

```go
func (r *ReflectionAgent) buildCritiquePrompt(originalQuery, currentOutput string) *agenkit.Message {
    var b strings.Builder
    b.Grow(len(originalQuery) + len(currentOutput) + 500)  // Pre-allocate

    if r.critiqueFormat == CritiqueStructured {
        b.WriteString("Please evaluate the following output and provide structured feedback.\n\n")
        b.WriteString("Original Request:\n")
        b.WriteString(originalQuery)
        b.WriteString("\n\nCurrent Output:\n")
        b.WriteString(currentOutput)
        b.WriteString("\n\n...")
    }

    return agenkit.NewMessage("user", b.String())
}
```

**Expected Savings**: 5-10 μs per call, ~2-4% total improvement

---

## Implementation Plan

### Phase 1: Critical Fix (30 minutes)

1. ✅ **Identify root cause** - Complete
2. 🔲 **Pre-compile regexes** - Implement package-level variables
3. 🔲 **Test functionality** - Ensure tests still pass
4. 🔲 **Benchmark improvement** - Verify 5x+ speedup

### Phase 2: Secondary Optimization (15 minutes)

5. 🔲 **Optimize string building** - Use strings.Builder
6. 🔲 **Benchmark improvement** - Verify additional 2-4% gain

### Phase 3: Verification (15 minutes)

7. 🔲 **Run full benchmark suite** - Ensure no regressions
8. 🔲 **Update documentation** - Reflect new performance characteristics
9. 🔲 **Update performance matrix** - Document improvement

**Total Estimated Time**: 1 hour

---

## Testing Strategy

### Unit Tests

Existing tests should continue to pass:
- `TestReflectionAgent` in `agenkit-go/patterns/reflection_test.go`
- All reflection-related integration tests

### Benchmark Verification

```bash
cd /Users/scttfrdmn/src/agenkit/agenkit-go/benchmarks

# Before optimization
go test -bench=BenchmarkReflection -benchmem -run=^$ > before.txt

# After optimization (implement fix)
go test -bench=BenchmarkReflection -benchmem -run=^$ > after.txt

# Compare results
go install golang.org/x/perf/cmd/benchstat@latest
benchstat before.txt after.txt
```

**Expected Output**:
```
name             old time/op    new time/op    delta
Reflection-12      248µs ± 2%      48µs ± 2%  -80.65%  ✅

name             old alloc/op   new alloc/op   delta
Reflection-12     35.0kB ± 0%     1.8kB ± 0%  -94.86%  ✅

name             old allocs/op  new allocs/op  delta
Reflection-12       298 ± 0%        20 ± 0%  -93.29%  ✅
```

---

## Lessons Learned

### Performance Anti-Patterns in Go

1. **Never compile regexes in hot loops**
   - Pre-compile at package level
   - Use `sync.Once` if needed for initialization

2. **Profile before optimizing**
   - CPU profile reveals hot paths
   - Memory profile reveals allocation sources
   - Don't guess, measure

3. **Cross-language parity requires similar algorithms**
   - Python pre-compiles regexes → Go should too
   - Match implementation strategies across languages

4. **Benchmark regression detection is critical**
   - This issue would have been caught in CI if we had benchmark baselines
   - Add to GitHub Actions workflow

### Future Improvements

1. **Add benchmark regression testing to CI**
   - Track performance baselines
   - Alert on >10% regressions

2. **Regular cross-language performance audits**
   - Compare implementations quarterly
   - Identify divergences early

3. **Document performance expectations**
   - Add performance notes to pattern documentation
   - Set acceptable ranges for each pattern

---

## References

- **Go Regex Documentation**: https://pkg.go.dev/regexp
- **Python re Module**: https://docs.python.org/3/library/re.html
- **Go Profiling Guide**: https://go.dev/blog/pprof
- **Benchmark Results**: `docs/PATTERN_PERFORMANCE_MATRIX.md`

---

**Next Step**: Implement the fix and verify the improvement.
