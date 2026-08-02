#!/bin/bash
# Test Parity Tracking Script
# Runs all test suites across 9 languages and generates parity report
#
# PERFORMANCE OPTIMIZATION (v0.49.0):
# - Rust counting now uses grep on source files instead of cargo test
# - Improvement: ~600x faster (0.1s vs 10min), 99.9% less memory (<10MB vs 4GB)
# - Prevents OOM kills on systems with limited RAM/swap space
# - More accurate: counts actual test annotations, not cargo output

set -e
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_JSON="$PROJECT_ROOT/test-parity-report.json"
REPORT_MD="$PROJECT_ROOT/docs/TEST_PARITY.md"

cd "$PROJECT_ROOT"

echo "=== Agenkit Test Parity Report ==="
echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# Initialize JSON report
cat > "$REPORT_JSON" << 'EOF'
{
  "generated_at": "",
  "languages": {}
}
EOF

# Update timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
jq --arg ts "$TIMESTAMP" '.generated_at = $ts' "$REPORT_JSON" > "$REPORT_JSON.tmp" && mv "$REPORT_JSON.tmp" "$REPORT_JSON"

# require_language <name>
# Assert a language actually landed in the report.
#
# `set -e` does NOT fire on the left-hand side of `&&`, so every
# `jq ... > tmp && mv tmp $REPORT_JSON` block below can fail -- a jq syntax
# error, a bad --arg -- while the script sails on and exits 0. That is exactly
# how Zig silently vanished from the report during #757: jq rejected the filter,
# `mv` never ran, and the only evidence was one line of stderr in a 700-line log.
# Call this after each write so a dropped language is fatal and named.
require_language() {
    local lang="$1"
    if ! jq -e --arg l "$lang" 'has("languages") and (.languages | has($l))' \
            "$REPORT_JSON" > /dev/null 2>&1; then
        echo "ERROR: '$lang' is missing from $REPORT_JSON after its write step." >&2
        echo "       The jq filter for $lang failed (check stderr above)." >&2
        exit 1
    fi
}

#==============================================================================
# PYTHON
#==============================================================================
echo "=== Python Test Counts ==="

# Total Python tests
PYTHON_TOTAL=$(uv run pytest tests/ --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
echo "Total: $PYTHON_TOTAL"

# Python by category
PYTHON_PATTERNS=$(uv run pytest tests/patterns --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_TECHNIQUES=$(uv run pytest tests/techniques --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_SAFETY=$(uv run pytest tests/safety --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_ADAPTERS=$(uv run pytest tests/adapters --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_EVALUATION=$(uv run pytest tests/evaluation --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_MIDDLEWARE=$(uv run pytest tests/middleware --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_MEMORY=$(uv run pytest tests/memory --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_ROUTING=$(uv run pytest tests/routing --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_CHAOS=$(uv run pytest tests/chaos --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_PROPERTY=$(uv run pytest tests/property --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_BUDGET=$(uv run pytest tests/budget --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_OBSERVABILITY=$(uv run pytest tests/observability --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_INTEGRATION=$(uv run pytest tests/integration --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_TOOLS=$(uv run pytest tests/tools --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")
PYTHON_COMPOSITION=$(uv run pytest tests/composition --collect-only -q 2>&1 | grep -E "^[0-9]+ tests? collected" | awk '{print $1}' || echo "0")

echo "  Patterns: $PYTHON_PATTERNS"
echo "  Techniques: $PYTHON_TECHNIQUES"
echo "  Safety: $PYTHON_SAFETY"
echo "  Adapters: $PYTHON_ADAPTERS"
echo "  Evaluation: $PYTHON_EVALUATION"
echo "  Middleware: $PYTHON_MIDDLEWARE"
echo "  Memory: $PYTHON_MEMORY"
echo "  Routing: $PYTHON_ROUTING"
echo "  Chaos: $PYTHON_CHAOS"
echo "  Property: $PYTHON_PROPERTY"
echo "  Budget: $PYTHON_BUDGET"
echo "  Observability: $PYTHON_OBSERVABILITY"
echo "  Integration: $PYTHON_INTEGRATION"
echo "  Tools: $PYTHON_TOOLS"
echo "  Composition: $PYTHON_COMPOSITION"
echo ""

# Add Python to JSON
jq --arg total "$PYTHON_TOTAL" \
   --arg patterns "$PYTHON_PATTERNS" \
   --arg techniques "$PYTHON_TECHNIQUES" \
   --arg safety "$PYTHON_SAFETY" \
   --arg adapters "$PYTHON_ADAPTERS" \
   --arg evaluation "$PYTHON_EVALUATION" \
   --arg middleware "$PYTHON_MIDDLEWARE" \
   --arg memory "$PYTHON_MEMORY" \
   --arg routing "$PYTHON_ROUTING" \
   --arg chaos "$PYTHON_CHAOS" \
   --arg property "$PYTHON_PROPERTY" \
   --arg budget "$PYTHON_BUDGET" \
   --arg observability "$PYTHON_OBSERVABILITY" \
   --arg integration "$PYTHON_INTEGRATION" \
   --arg tools "$PYTHON_TOOLS" \
   --arg composition "$PYTHON_COMPOSITION" \
   '.languages.python = {
     total: ($total | tonumber),
     categories: {
       patterns: ($patterns | tonumber),
       techniques: ($techniques | tonumber),
       safety: ($safety | tonumber),
       adapters: ($adapters | tonumber),
       evaluation: ($evaluation | tonumber),
       middleware: ($middleware | tonumber),
       memory: ($memory | tonumber),
       routing: ($routing | tonumber),
       chaos: ($chaos | tonumber),
       property: ($property | tonumber),
       budget: ($budget | tonumber),
       observability: ($observability | tonumber),
       integration: ($integration | tonumber),
       tools: ($tools | tonumber),
       composition: ($composition | tonumber)
     }
   }' "$REPORT_JSON" > "$REPORT_JSON.tmp" && mv "$REPORT_JSON.tmp" "$REPORT_JSON"
require_language python

#==============================================================================
# GO
#==============================================================================
echo "=== Go Test Counts ==="

cd agenkit-go
GO_TOTAL=$(go test ./... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')
echo "Total: $GO_TOTAL"

# Go by module (approximate from file counts and test runs)
GO_PATTERNS=$(find patterns -name "*_test.go" | wc -l | tr -d ' ')
GO_PATTERNS_TESTS=$(go test ./patterns/... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')
GO_TECHNIQUES=$(find techniques -name "*_test.go" 2>/dev/null | wc -l | tr -d ' ')
GO_TECHNIQUES_TESTS=$(go test ./techniques/... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')
GO_SAFETY=$(find safety -name "*_test.go" 2>/dev/null | wc -l | tr -d ' ')
GO_SAFETY_TESTS=$(go test ./safety/... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')
GO_ADAPTERS=$(find adapter -name "*_test.go" 2>/dev/null | wc -l | tr -d ' ')
GO_ADAPTERS_TESTS=$(go test ./adapter/... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')
GO_EVALUATION=$(find evaluation -name "*_test.go" 2>/dev/null | wc -l | tr -d ' ')
GO_EVALUATION_TESTS=$(go test ./evaluation/... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')
GO_MIDDLEWARE=$(find middleware -name "*_test.go" 2>/dev/null | wc -l | tr -d ' ')
GO_MIDDLEWARE_TESTS=$(go test ./middleware/... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')
GO_MEMORY=$(find memory -name "*_test.go" 2>/dev/null | wc -l | tr -d ' ')
GO_MEMORY_TESTS=$(go test ./memory/... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')
GO_TOOLS=$(find tools -name "*_test.go" 2>/dev/null | wc -l | tr -d ' ')
GO_TOOLS_TESTS=$(go test ./tools/... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')
GO_OBSERVABILITY=$(find observability -name "*_test.go" 2>/dev/null | wc -l | tr -d ' ')
GO_OBSERVABILITY_TESTS=$(go test ./observability/... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')
GO_COMPOSITION=$(find composition -name "*_test.go" 2>/dev/null | wc -l | tr -d ' ')
GO_COMPOSITION_TESTS=$(go test ./composition/... -v 2>&1 | grep -E "^--- (PASS|FAIL):" | wc -l | tr -d ' ')

echo "  Patterns: $GO_PATTERNS_TESTS (files: $GO_PATTERNS)"
echo "  Techniques: $GO_TECHNIQUES_TESTS (files: $GO_TECHNIQUES)"
echo "  Safety: $GO_SAFETY_TESTS (files: $GO_SAFETY)"
echo "  Adapters: $GO_ADAPTERS_TESTS (files: $GO_ADAPTERS)"
echo "  Evaluation: $GO_EVALUATION_TESTS (files: $GO_EVALUATION)"
echo "  Middleware: $GO_MIDDLEWARE_TESTS (files: $GO_MIDDLEWARE)"
echo "  Memory: $GO_MEMORY_TESTS (files: $GO_MEMORY)"
echo "  Tools: $GO_TOOLS_TESTS (files: $GO_TOOLS)"
echo "  Observability: $GO_OBSERVABILITY_TESTS (files: $GO_OBSERVABILITY)"
echo "  Composition: $GO_COMPOSITION_TESTS (files: $GO_COMPOSITION)"
echo "  Routing: 0 (not implemented)"
echo "  Chaos: 0 (not implemented)"
echo "  Property: 0 (not implemented)"
echo ""

cd "$PROJECT_ROOT"

# Add Go to JSON
jq --arg total "$GO_TOTAL" \
   --arg patterns "$GO_PATTERNS_TESTS" \
   --arg techniques "$GO_TECHNIQUES_TESTS" \
   --arg safety "$GO_SAFETY_TESTS" \
   --arg adapters "$GO_ADAPTERS_TESTS" \
   --arg evaluation "$GO_EVALUATION_TESTS" \
   --arg middleware "$GO_MIDDLEWARE_TESTS" \
   --arg memory "$GO_MEMORY_TESTS" \
   --arg tools "$GO_TOOLS_TESTS" \
   --arg observability "$GO_OBSERVABILITY_TESTS" \
   --arg composition "$GO_COMPOSITION_TESTS" \
   '.languages.go = {
     total: ($total | tonumber),
     categories: {
       patterns: ($patterns | tonumber),
       techniques: ($techniques | tonumber),
       safety: ($safety | tonumber),
       adapters: ($adapters | tonumber),
       evaluation: ($evaluation | tonumber),
       middleware: ($middleware | tonumber),
       memory: ($memory | tonumber),
       routing: 0,
       chaos: 0,
       property: 0,
       tools: ($tools | tonumber),
       observability: ($observability | tonumber),
       composition: ($composition | tonumber)
     }
   }' "$REPORT_JSON" > "$REPORT_JSON.tmp" && mv "$REPORT_JSON.tmp" "$REPORT_JSON"
require_language go

#==============================================================================
# C++
#==============================================================================
echo "=== C++ Test Counts ==="

if [ -d "agenkit-cpp/tests" ]; then
    # Count individual TEST() macros instead of test suites
    # This gives a more accurate count comparable to other languages
    CPP_TOTAL=$(find agenkit-cpp/tests -name "test_*.cpp" -exec grep -h "TEST(" {} \; | wc -l | tr -d ' ')
    echo "Total: $CPP_TOTAL tests"

    # C++ by category (count TEST macros per category)
    CPP_PATTERNS=$(find agenkit-cpp/tests/patterns -name "test_*.cpp" -exec grep -h "TEST(" {} \; 2>/dev/null | wc -l | tr -d ' ')
    CPP_TECHNIQUES=$(find agenkit-cpp/tests/techniques -name "test_*.cpp" -exec grep -h "TEST(" {} \; 2>/dev/null | wc -l | tr -d ' ')
    CPP_UNIT=$(find agenkit-cpp/tests/unit -name "test_*.cpp" -exec grep -h "TEST(" {} \; 2>/dev/null | wc -l | tr -d ' ')
    CPP_INTEGRATION=$(find agenkit-cpp/tests/integration -name "test_*.cpp" -exec grep -h "TEST(" {} \; 2>/dev/null | wc -l | tr -d ' ')

    # Count test files for reference
    CPP_PATTERNS_FILES=$(find agenkit-cpp/tests/patterns -name "test_*.cpp" 2>/dev/null | wc -l | tr -d ' ')
    CPP_TECHNIQUES_FILES=$(find agenkit-cpp/tests/techniques -name "test_*.cpp" 2>/dev/null | wc -l | tr -d ' ')
    CPP_UNIT_FILES=$(find agenkit-cpp/tests/unit -name "test_*.cpp" 2>/dev/null | wc -l | tr -d ' ')
    CPP_INTEGRATION_FILES=$(find agenkit-cpp/tests/integration -name "test_*.cpp" 2>/dev/null | wc -l | tr -d ' ')

    echo "  Patterns: $CPP_PATTERNS (files: $CPP_PATTERNS_FILES)"
    echo "  Techniques: $CPP_TECHNIQUES (files: $CPP_TECHNIQUES_FILES)"
    echo "  Unit: $CPP_UNIT (files: $CPP_UNIT_FILES)"
    echo "  Integration: $CPP_INTEGRATION (files: $CPP_INTEGRATION_FILES)"
    echo "  Safety: 0 (not implemented)"
    echo "  Adapters: ~50 (in integration)"
    echo "  Routing: 0 (not implemented)"
    echo "  Chaos: 0 (not implemented)"
    echo ""

    # Add C++ to JSON
    jq --arg total "$CPP_TOTAL" \
       --arg patterns "$CPP_PATTERNS" \
       --arg techniques "$CPP_TECHNIQUES" \
       --arg unit "$CPP_UNIT" \
       --arg integration "$CPP_INTEGRATION" \
       '.languages.cpp = {
         total: ($total | tonumber),
         note: "C++ counts individual TEST() macros",
         categories: {
           patterns: ($patterns | tonumber),
           techniques: ($techniques | tonumber),
           unit: ($unit | tonumber),
           integration: ($integration | tonumber),
           safety: 0,
           adapters: 50,
           routing: 0,
           chaos: 0,
           property: 0
         }
       }' "$REPORT_JSON" > "$REPORT_JSON.tmp" && mv "$REPORT_JSON.tmp" "$REPORT_JSON"
    require_language cpp
else
    echo "C++ build directory not found. Skipping C++ tests."
    echo ""
fi

#==============================================================================
# RUST
#==============================================================================
echo "=== Rust Test Counts ==="

# Fast grep-based counting (avoids slow cargo compilation)
# Count all test annotations in source files
cd agenkit-rust || exit 1
RUST_TEST_COUNT=$(grep -r "#\[test\]" src/ tests/ 2>/dev/null | wc -l | tr -d ' ')
RUST_TOKIO_TEST_COUNT=$(grep -r "#\[tokio::test\]" src/ tests/ 2>/dev/null | wc -l | tr -d ' ')
RUST_TOTAL=$((RUST_TEST_COUNT + RUST_TOKIO_TEST_COUNT))
cd ..

echo "Total: $RUST_TOTAL"

# Count by category (count test annotations in each directory)
cd agenkit-rust || exit 1
RUST_PATTERNS=$(grep -rh "#\[test\]\|#\[tokio::test\]" src/patterns/ 2>/dev/null | wc -l | tr -d ' ')
RUST_EVALUATION=$(grep -rh "#\[test\]\|#\[tokio::test\]" src/evaluation/ 2>/dev/null | wc -l | tr -d ' ')
RUST_OBSERVABILITY=$(grep -rh "#\[test\]\|#\[tokio::test\]" tests/test_observability_*.rs 2>/dev/null | wc -l | tr -d ' ')
RUST_TECHNIQUES=$(grep -rh "#\[test\]\|#\[tokio::test\]" src/techniques/ 2>/dev/null | wc -l | tr -d ' ')
RUST_ADAPTERS=$(grep -rh "#\[test\]\|#\[tokio::test\]" src/adapters/ 2>/dev/null | wc -l | tr -d ' ')
RUST_SAFETY=$(grep -rh "#\[test\]\|#\[tokio::test\]" src/safety/ 2>/dev/null | wc -l | tr -d ' ')
cd ..

echo "  Patterns: $RUST_PATTERNS"
echo "  Techniques: $RUST_TECHNIQUES"
echo "  Adapters: $RUST_ADAPTERS"
echo "  Evaluation: $RUST_EVALUATION"
echo "  Observability: $RUST_OBSERVABILITY"
echo "  Safety: $RUST_SAFETY"
echo "  Routing: 0 (not implemented)"
echo "  Chaos: 0 (not implemented)"
echo ""

# Add Rust to JSON
jq --arg total "$RUST_TOTAL" \
   --arg patterns "$RUST_PATTERNS" \
   --arg techniques "$RUST_TECHNIQUES" \
   --arg adapters "$RUST_ADAPTERS" \
   --arg evaluation "$RUST_EVALUATION" \
   --arg observability "$RUST_OBSERVABILITY" \
   --arg safety "$RUST_SAFETY" \
   '.languages.rust = {
     total: ($total | tonumber),
     categories: {
       patterns: ($patterns | tonumber),
       techniques: ($techniques | tonumber),
       adapters: ($adapters | tonumber),
       evaluation: ($evaluation | tonumber),
       observability: ($observability | tonumber),
       safety: ($safety | tonumber),
       routing: 0,
       chaos: 0,
       property: 0
     }
   }' "$REPORT_JSON" > "$REPORT_JSON.tmp" && mv "$REPORT_JSON.tmp" "$REPORT_JSON"
require_language rust

#==============================================================================
# ZIG
#==============================================================================
echo "=== Zig Test Counts ==="

cd agenkit-zig
# `--summary all` is required: plain `zig build test` prints no aggregate count,
# so the old grep for "N tests passed" never matched and silently fell back to a
# hardcoded "214". Zig's real total is 496 -- the report understated it by 2.3x
# for as long as that fallback existed, and because 214 was a plausible value
# there was no way to tell from the report that counting was broken. See #757.
ZIG_OUTPUT=$(zig build test --summary all 2>&1 || true)
ZIG_TOTAL=$(echo "$ZIG_OUTPUT" | grep -oE "[0-9]+/[0-9]+ tests passed" | head -1 | cut -d/ -f1)
if [ -z "$ZIG_TOTAL" ]; then
    echo "ERROR: could not parse a test count from 'zig build test --summary all'." >&2
    echo "       The build failed or its summary format changed. Output was:" >&2
    echo "$ZIG_OUTPUT" | tail -20 >&2
    exit 1
fi
echo "Total: $ZIG_TOTAL"

cd "$PROJECT_ROOT"

# Zig tests are in-code, hard to categorize
echo "  (Zig uses in-code tests - category breakdown unavailable)"
echo ""

# Add Zig to JSON
jq --arg total "$ZIG_TOTAL" \
   '.languages.zig = {
     total: ($total | tonumber),
     note: "Counted from the summary line of zig build test --summary all; in-code tests have no clear category separation",
     categories: {}
   }' "$REPORT_JSON" > "$REPORT_JSON.tmp" && mv "$REPORT_JSON.tmp" "$REPORT_JSON"
require_language zig

#==============================================================================
# TYPESCRIPT
#==============================================================================
echo "=== TypeScript Test Counts ==="

TS_FILES=$(find agenkit-ts -name "*.test.ts" -o -name "*.spec.ts" 2>/dev/null | wc -l | tr -d ' ')
echo "Test files: $TS_FILES"

# Try to get actual test count from npm test
cd agenkit-ts
TS_OUTPUT=$(npm test 2>&1 || true)
TS_TOTAL=$(echo "$TS_OUTPUT" | grep -oE "Tests:.*[0-9]+ passed" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" | head -1 || echo "0")

if [ -z "$TS_TOTAL" ] || [ "$TS_TOTAL" -eq "0" ]; then
    # Fallback: estimate from files
    if [ "$TS_FILES" -gt "0" ]; then
        TS_TOTAL=$((TS_FILES * 8))
        echo "Total: ~$TS_TOTAL (estimated from $TS_FILES files)"
    else
        TS_TOTAL="328"
        echo "Total: $TS_TOTAL (fallback)"
    fi
else
    echo "Total: $TS_TOTAL"
fi

cd "$PROJECT_ROOT"

# TypeScript by category (from file locations and test counts)
TS_PATTERNS=$(find agenkit-ts/src/__tests__/patterns -name "*.test.ts" 2>/dev/null | wc -l | tr -d ' ')
TS_CORE=$(find agenkit-ts/src -maxdepth 3 -name "*.test.ts" 2>/dev/null | wc -l | tr -d ' ')

# Count tests in chaos, property, integration, safety, techniques, adapters, and evaluation directories
TS_CHAOS=$(grep -r "it(" agenkit-ts/src/__tests__/chaos/ 2>/dev/null | wc -l | tr -d ' ')
TS_PROPERTY=$(grep -r "it(" agenkit-ts/src/__tests__/property/ 2>/dev/null | wc -l | tr -d ' ')
TS_INTEGRATION=$(grep -r "it(" agenkit-ts/src/__tests__/integration/ 2>/dev/null | wc -l | tr -d ' ')
TS_SAFETY=$(grep -r "it(" agenkit-ts/src/__tests__/safety/ 2>/dev/null | wc -l | tr -d ' ')
TS_TECHNIQUES=$(grep -r "it(" agenkit-ts/src/techniques/ 2>/dev/null | wc -l | tr -d ' ')
TS_ADAPTERS=$(grep -r "it(" agenkit-ts/src/__tests__/adapters/ 2>/dev/null | wc -l | tr -d ' ')
TS_EVALUATION=$(grep -r "it(" agenkit-ts/src/__tests__/evaluation/ 2>/dev/null | wc -l | tr -d ' ')

echo "  Pattern tests: $TS_PATTERNS files"
echo "  Core tests: $TS_CORE files"
echo "  Chaos tests: $TS_CHAOS"
echo "  Property tests: $TS_PROPERTY"
echo "  Integration tests: $TS_INTEGRATION"
echo "  Safety tests: $TS_SAFETY"
echo "  Techniques tests: $TS_TECHNIQUES"
echo "  Adapters tests: $TS_ADAPTERS"
echo "  Evaluation tests: $TS_EVALUATION"
echo ""

# Add TypeScript to JSON
jq --arg total "$TS_TOTAL" \
   --arg files "$TS_FILES" \
   --arg patterns "$TS_PATTERNS" \
   --arg chaos "$TS_CHAOS" \
   --arg property "$TS_PROPERTY" \
   --arg integration "$TS_INTEGRATION" \
   --arg safety "$TS_SAFETY" \
   --arg techniques "$TS_TECHNIQUES" \
   --arg adapters "$TS_ADAPTERS" \
   --arg evaluation "$TS_EVALUATION" \
   '.languages.typescript = {
     total: ($total | tonumber),
     test_files: ($files | tonumber),
     note: "Counts may be estimated from test files",
     categories: {
       patterns: ($patterns | tonumber),
       techniques: ($techniques | tonumber),
       safety: ($safety | tonumber),
       adapters: ($adapters | tonumber),
       evaluation: ($evaluation | tonumber),
       routing: 0,
       chaos: ($chaos | tonumber),
       property: ($property | tonumber),
       integration: ($integration | tonumber)
     }
   }' "$REPORT_JSON" > "$REPORT_JSON.tmp" && mv "$REPORT_JSON.tmp" "$REPORT_JSON"
require_language typescript

#==============================================================================
# C# / JAVA / SCALA
#==============================================================================
# These three were absent from the report entirely, which made every threshold
# in tests/test_parity_validation.py inert for them: test_total_parity_threshold
# calls pytest.skip when a language is missing, so C#/Java/Scala could have lost
# every test without failing anything. See #757.
#
# Counted by grep rather than by building, matching the Rust approach above (see
# the v0.49.0 note on speed and OOM avoidance). Verified against real runs:
# Java 358 = grep 358, Scala 363 = grep 363, C# 276 real vs 272 grep. The C#
# delta is one [Theory] whose InlineData rows expand into several cases at
# runtime; undercounting is the safe direction for a regression floor.

# count_annotations <extended-regex> <dir>...
# Emits the number of matches across the given directories, 0 if none exist.
count_annotations() {
    local pattern="$1"
    shift
    local dirs=()
    local d
    for d in "$@"; do
        [ -d "$d" ] && dirs+=("$d")
    done
    if [ ${#dirs[@]} -eq 0 ]; then
        echo "0"
        return
    fi
    grep -rhoE "$pattern" "${dirs[@]}" 2>/dev/null | wc -l | tr -d ' '
}

echo "=== C# Test Counts ==="

CS_TEST_ROOT="agenkit-cs/tests"
CS_ANNOTATION='\[(Fact|Theory)\]'
CS_TOTAL=$(count_annotations "$CS_ANNOTATION" "$CS_TEST_ROOT")

# A zero here means the layout moved, not that the tests vanished -- C# has had
# 241+ tests since v0.71.0. Fail loudly rather than recording a bogus 0 that
# every downstream threshold would then validate against.
if [ "$CS_TOTAL" -eq 0 ]; then
    echo "ERROR: counted 0 C# tests under $CS_TEST_ROOT -- layout moved or annotation style changed" >&2
    exit 1
fi
echo "Total: $CS_TOTAL"

CS_PATTERNS=$(count_annotations "$CS_ANNOTATION" "$CS_TEST_ROOT/Agenkit.Tests/Patterns")
CS_TECHNIQUES=$(count_annotations "$CS_ANNOTATION" "$CS_TEST_ROOT/Agenkit.Tests/Techniques")
CS_MIDDLEWARE=$(count_annotations "$CS_ANNOTATION" "$CS_TEST_ROOT/Agenkit.Tests/Middleware")
CS_MEMORY=$(count_annotations "$CS_ANNOTATION" "$CS_TEST_ROOT/Agenkit.Tests/Memory")
CS_SAFETY=$(count_annotations "$CS_ANNOTATION" "$CS_TEST_ROOT/Agenkit.Tests/Safety")
CS_ADAPTERS=$(count_annotations "$CS_ANNOTATION" "$CS_TEST_ROOT/Agenkit.Tests/Adapters")
CS_EVALUATION=$(count_annotations "$CS_ANNOTATION" "$CS_TEST_ROOT/Agenkit.Tests/Evaluation")
CS_OBSERVABILITY=$(count_annotations "$CS_ANNOTATION" "$CS_TEST_ROOT/Agenkit.Tests/Observability")
CS_BUDGET=$(count_annotations "$CS_ANNOTATION" "$CS_TEST_ROOT/Agenkit.Tests/Budget")

echo "  Patterns: $CS_PATTERNS"
echo "  Techniques: $CS_TECHNIQUES (no techniques subsystem -- see #754)"
echo "  Middleware: $CS_MIDDLEWARE"
echo "  Memory: $CS_MEMORY"
echo "  Safety: $CS_SAFETY"
echo "  Adapters: $CS_ADAPTERS"
echo "  Evaluation: $CS_EVALUATION"
echo "  Observability: $CS_OBSERVABILITY"
echo "  Budget: $CS_BUDGET"
echo ""

jq --arg total "$CS_TOTAL" \
   --arg patterns "$CS_PATTERNS" \
   --arg techniques "$CS_TECHNIQUES" \
   --arg middleware "$CS_MIDDLEWARE" \
   --arg memory "$CS_MEMORY" \
   --arg safety "$CS_SAFETY" \
   --arg adapters "$CS_ADAPTERS" \
   --arg evaluation "$CS_EVALUATION" \
   --arg observability "$CS_OBSERVABILITY" \
   --arg budget "$CS_BUDGET" \
   '.languages.csharp = {
     total: ($total | tonumber),
     note: "Counted from [Fact]/[Theory] annotations; a [Theory] expands to multiple cases at runtime, so this slightly undercounts",
     categories: {
       patterns: ($patterns | tonumber),
       techniques: ($techniques | tonumber),
       middleware: ($middleware | tonumber),
       memory: ($memory | tonumber),
       safety: ($safety | tonumber),
       adapters: ($adapters | tonumber),
       evaluation: ($evaluation | tonumber),
       observability: ($observability | tonumber),
       budget: ($budget | tonumber),
       routing: 0,
       chaos: 0,
       property: 0
     }
   }' "$REPORT_JSON" > "$REPORT_JSON.tmp" && mv "$REPORT_JSON.tmp" "$REPORT_JSON"
require_language csharp

echo "=== Java Test Counts ==="

JAVA_TEST_ROOT="agenkit-java/src/test/java/io/agenkit"
JAVA_ANNOTATION='@(Test|ParameterizedTest|Property)\b'
JAVA_TOTAL=$(count_annotations "$JAVA_ANNOTATION" "$JAVA_TEST_ROOT")

if [ "$JAVA_TOTAL" -eq 0 ]; then
    echo "ERROR: counted 0 Java tests under $JAVA_TEST_ROOT -- layout moved or annotation style changed" >&2
    exit 1
fi
echo "Total: $JAVA_TOTAL"

JAVA_PATTERNS=$(count_annotations "$JAVA_ANNOTATION" "$JAVA_TEST_ROOT/patterns")
JAVA_TECHNIQUES=$(count_annotations "$JAVA_ANNOTATION" "$JAVA_TEST_ROOT/techniques")
JAVA_MIDDLEWARE=$(count_annotations "$JAVA_ANNOTATION" "$JAVA_TEST_ROOT/middleware")
JAVA_MEMORY=$(count_annotations "$JAVA_ANNOTATION" "$JAVA_TEST_ROOT/memory")
JAVA_SAFETY=$(count_annotations "$JAVA_ANNOTATION" "$JAVA_TEST_ROOT/safety")
JAVA_ADAPTERS=$(count_annotations "$JAVA_ANNOTATION" "$JAVA_TEST_ROOT/adapters")
JAVA_EVALUATION=$(count_annotations "$JAVA_ANNOTATION" "$JAVA_TEST_ROOT/evaluation")
JAVA_OBSERVABILITY=$(count_annotations "$JAVA_ANNOTATION" "$JAVA_TEST_ROOT/observability")
JAVA_BUDGET=$(count_annotations "$JAVA_ANNOTATION" "$JAVA_TEST_ROOT/budget")
JAVA_PROPERTY=$(count_annotations '@Property\b' "$JAVA_TEST_ROOT")

echo "  Patterns: $JAVA_PATTERNS"
echo "  Techniques: $JAVA_TECHNIQUES (no techniques subsystem -- see #754)"
echo "  Middleware: $JAVA_MIDDLEWARE"
echo "  Memory: $JAVA_MEMORY"
echo "  Safety: $JAVA_SAFETY"
echo "  Adapters: $JAVA_ADAPTERS"
echo "  Evaluation: $JAVA_EVALUATION"
echo "  Observability: $JAVA_OBSERVABILITY"
echo "  Budget: $JAVA_BUDGET"
echo "  Property: $JAVA_PROPERTY"
echo ""

jq --arg total "$JAVA_TOTAL" \
   --arg patterns "$JAVA_PATTERNS" \
   --arg techniques "$JAVA_TECHNIQUES" \
   --arg middleware "$JAVA_MIDDLEWARE" \
   --arg memory "$JAVA_MEMORY" \
   --arg safety "$JAVA_SAFETY" \
   --arg adapters "$JAVA_ADAPTERS" \
   --arg evaluation "$JAVA_EVALUATION" \
   --arg observability "$JAVA_OBSERVABILITY" \
   --arg budget "$JAVA_BUDGET" \
   --arg property "$JAVA_PROPERTY" \
   '.languages.java = {
     total: ($total | tonumber),
     note: "Counted from @Test/@ParameterizedTest/@Property annotations (jqwik + JUnit 5)",
     categories: {
       patterns: ($patterns | tonumber),
       techniques: ($techniques | tonumber),
       middleware: ($middleware | tonumber),
       memory: ($memory | tonumber),
       safety: ($safety | tonumber),
       adapters: ($adapters | tonumber),
       evaluation: ($evaluation | tonumber),
       observability: ($observability | tonumber),
       budget: ($budget | tonumber),
       property: ($property | tonumber),
       routing: 0,
       chaos: 0
     }
   }' "$REPORT_JSON" > "$REPORT_JSON.tmp" && mv "$REPORT_JSON.tmp" "$REPORT_JSON"
require_language java

echo "=== Scala Test Counts ==="

SCALA_TEST_ROOT="agenkit-scala/src/test/scala/io/agenkit"
# munit/ScalaCheck declare cases as `test("...")` / `property("...")` at the
# start of a line, so anchor to avoid matching the words inside comments or
# nested helper calls.
SCALA_ANNOTATION='^[[:space:]]*(test|property)[[:space:]]*\('
SCALA_TOTAL=$(count_annotations "$SCALA_ANNOTATION" "$SCALA_TEST_ROOT")

if [ "$SCALA_TOTAL" -eq 0 ]; then
    echo "ERROR: counted 0 Scala tests under $SCALA_TEST_ROOT -- layout moved or test style changed" >&2
    exit 1
fi
echo "Total: $SCALA_TOTAL"

SCALA_PATTERNS=$(count_annotations "$SCALA_ANNOTATION" "$SCALA_TEST_ROOT/patterns")
SCALA_TECHNIQUES=$(count_annotations "$SCALA_ANNOTATION" "$SCALA_TEST_ROOT/techniques")
SCALA_MIDDLEWARE=$(count_annotations "$SCALA_ANNOTATION" "$SCALA_TEST_ROOT/middleware")
SCALA_MEMORY=$(count_annotations "$SCALA_ANNOTATION" "$SCALA_TEST_ROOT/memory")
SCALA_SAFETY=$(count_annotations "$SCALA_ANNOTATION" "$SCALA_TEST_ROOT/safety")
SCALA_ADAPTERS=$(count_annotations "$SCALA_ANNOTATION" "$SCALA_TEST_ROOT/adapters")
SCALA_EVALUATION=$(count_annotations "$SCALA_ANNOTATION" "$SCALA_TEST_ROOT/evaluation")
SCALA_OBSERVABILITY=$(count_annotations "$SCALA_ANNOTATION" "$SCALA_TEST_ROOT/observability")
SCALA_BUDGET=$(count_annotations "$SCALA_ANNOTATION" "$SCALA_TEST_ROOT/budget")
SCALA_PROPERTY=$(count_annotations '^[[:space:]]*property[[:space:]]*\(' "$SCALA_TEST_ROOT")

echo "  Patterns: $SCALA_PATTERNS"
echo "  Techniques: $SCALA_TECHNIQUES (no techniques subsystem -- see #754)"
echo "  Middleware: $SCALA_MIDDLEWARE"
echo "  Memory: $SCALA_MEMORY"
echo "  Safety: $SCALA_SAFETY"
echo "  Adapters: $SCALA_ADAPTERS"
echo "  Evaluation: $SCALA_EVALUATION"
echo "  Observability: $SCALA_OBSERVABILITY"
echo "  Budget: $SCALA_BUDGET"
echo "  Property: $SCALA_PROPERTY"
echo ""

jq --arg total "$SCALA_TOTAL" \
   --arg patterns "$SCALA_PATTERNS" \
   --arg techniques "$SCALA_TECHNIQUES" \
   --arg middleware "$SCALA_MIDDLEWARE" \
   --arg memory "$SCALA_MEMORY" \
   --arg safety "$SCALA_SAFETY" \
   --arg adapters "$SCALA_ADAPTERS" \
   --arg evaluation "$SCALA_EVALUATION" \
   --arg observability "$SCALA_OBSERVABILITY" \
   --arg budget "$SCALA_BUDGET" \
   --arg property "$SCALA_PROPERTY" \
   '.languages.scala = {
     total: ($total | tonumber),
     note: "Counted from munit test(...) / ScalaCheck property(...) declarations",
     categories: {
       patterns: ($patterns | tonumber),
       techniques: ($techniques | tonumber),
       middleware: ($middleware | tonumber),
       memory: ($memory | tonumber),
       safety: ($safety | tonumber),
       adapters: ($adapters | tonumber),
       evaluation: ($evaluation | tonumber),
       observability: ($observability | tonumber),
       budget: ($budget | tonumber),
       property: ($property | tonumber),
       routing: 0,
       chaos: 0
     }
   }' "$REPORT_JSON" > "$REPORT_JSON.tmp" && mv "$REPORT_JSON.tmp" "$REPORT_JSON"
require_language scala

#==============================================================================
# GENERATE MARKDOWN REPORT
#==============================================================================
echo "=== Generating Markdown Report ==="

cat > "$REPORT_MD" << 'MDHEADER'
# Test Parity Dashboard

**Last Updated:** AUTO_TIMESTAMP
**Status:** Tracking test parity across 9 language implementations

## Overview

This dashboard tracks test coverage across all Agenkit language implementations to ensure feature parity and quality consistency.

MDHEADER

# Replace timestamp placeholder
TIMESTAMP_STR=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/AUTO_TIMESTAMP/$TIMESTAMP_STR/" "$REPORT_MD"
else
    sed -i "s/AUTO_TIMESTAMP/$TIMESTAMP_STR/" "$REPORT_MD"
fi

# Add summary table
cat >> "$REPORT_MD" << 'MDTABLE'
## Test Count Summary

| Language | Total Tests | vs Python | Parity % | Status |
|----------|------------|-----------|----------|--------|
MDTABLE

# Extract values and calculate parity
PYTHON_TOTAL_VAL=$(jq -r '.languages.python.total' "$REPORT_JSON")
GO_TOTAL_VAL=$(jq -r '.languages.go.total' "$REPORT_JSON")
CPP_TOTAL_VAL=$(jq -r '.languages.cpp.total' "$REPORT_JSON")
RUST_TOTAL_VAL=$(jq -r '.languages.rust.total' "$REPORT_JSON")
ZIG_TOTAL_VAL=$(jq -r '.languages.zig.total' "$REPORT_JSON")
TS_TOTAL_VAL=$(jq -r '.languages.typescript.total' "$REPORT_JSON")
CS_TOTAL_VAL=$(jq -r '.languages.csharp.total' "$REPORT_JSON")
JAVA_TOTAL_VAL=$(jq -r '.languages.java.total' "$REPORT_JSON")
SCALA_TOTAL_VAL=$(jq -r '.languages.scala.total' "$REPORT_JSON")

# Calculate parity percentages
GO_PARITY=$(echo "scale=1; ($GO_TOTAL_VAL * 100) / $PYTHON_TOTAL_VAL" | bc)
CPP_PARITY=$(echo "scale=1; (($CPP_TOTAL_VAL * 15) * 100) / $PYTHON_TOTAL_VAL" | bc) # C++ suites ≈ 15x tests
RUST_PARITY=$(echo "scale=1; ($RUST_TOTAL_VAL * 100) / $PYTHON_TOTAL_VAL" | bc)
ZIG_PARITY=$(echo "scale=1; ($ZIG_TOTAL_VAL * 100) / $PYTHON_TOTAL_VAL" | bc)
TS_PARITY=$(echo "scale=1; ($TS_TOTAL_VAL * 100) / $PYTHON_TOTAL_VAL" | bc)
CS_PARITY=$(echo "scale=1; ($CS_TOTAL_VAL * 100) / $PYTHON_TOTAL_VAL" | bc)
JAVA_PARITY=$(echo "scale=1; ($JAVA_TOTAL_VAL * 100) / $PYTHON_TOTAL_VAL" | bc)
SCALA_PARITY=$(echo "scale=1; ($SCALA_TOTAL_VAL * 100) / $PYTHON_TOTAL_VAL" | bc)

# Status indicators
get_status() {
    parity=$1
    if (( $(echo "$parity >= 80" | bc -l) )); then
        echo "✅ Excellent"
    elif (( $(echo "$parity >= 60" | bc -l) )); then
        echo "🟢 Good"
    elif (( $(echo "$parity >= 40" | bc -l) )); then
        echo "🟡 Fair"
    elif (( $(echo "$parity >= 20" | bc -l) )); then
        echo "🟠 Poor"
    else
        echo "🔴 Critical"
    fi
}

cat >> "$REPORT_MD" << MDDATA
| **Python** | $PYTHON_TOTAL_VAL | — | 100% | ✅ Reference |
| **Go** | $GO_TOTAL_VAL | -$(($PYTHON_TOTAL_VAL - $GO_TOTAL_VAL)) | ${GO_PARITY}% | $(get_status $GO_PARITY) |
| **C++** | $CPP_TOTAL_VAL suites | —¹ | ${CPP_PARITY}% | $(get_status $CPP_PARITY) |
| **Rust** | $RUST_TOTAL_VAL | -$(($PYTHON_TOTAL_VAL - $RUST_TOTAL_VAL)) | ${RUST_PARITY}% | $(get_status $RUST_PARITY) |
| **Zig** | $ZIG_TOTAL_VAL | -$(($PYTHON_TOTAL_VAL - $ZIG_TOTAL_VAL)) | ${ZIG_PARITY}% | $(get_status $ZIG_PARITY) |
| **TypeScript** | $TS_TOTAL_VAL² | —² | ${TS_PARITY}% | $(get_status $TS_PARITY) |
| **C#** | $CS_TOTAL_VAL³ | -$(($PYTHON_TOTAL_VAL - $CS_TOTAL_VAL)) | ${CS_PARITY}% | $(get_status $CS_PARITY) |
| **Java** | $JAVA_TOTAL_VAL | -$(($PYTHON_TOTAL_VAL - $JAVA_TOTAL_VAL)) | ${JAVA_PARITY}% | $(get_status $JAVA_PARITY) |
| **Scala** | $SCALA_TOTAL_VAL | -$(($PYTHON_TOTAL_VAL - $SCALA_TOTAL_VAL)) | ${SCALA_PARITY}% | $(get_status $SCALA_PARITY) |

¹ C++ reports test suites not individual tests. Estimated ≈15 tests/suite = $(($CPP_TOTAL_VAL * 15)) total tests.
² TypeScript count may be estimated from test files.
³ C# counts \`[Fact]\`/\`[Theory]\` annotations; a \`[Theory]\` expands to several cases at runtime, so this slightly undercounts (272 counted vs 276 actual).

MDDATA

# Add category breakdown
cat >> "$REPORT_MD" << 'MDCAT'

## Category Breakdown

### Core Categories (Critical for Production)

| Category | Python | Go | C++ | Rust | Zig | TypeScript |
|----------|--------|-----|-----|------|-----|------------|
MDCAT

# Extract category values
PYTHON_PATTERNS=$(jq -r '.languages.python.categories.patterns' "$REPORT_JSON")
GO_PATTERNS=$(jq -r '.languages.go.categories.patterns' "$REPORT_JSON")
CPP_PATTERNS=$(jq -r '.languages.cpp.categories.patterns' "$REPORT_JSON")
RUST_PATTERNS=$(jq -r '.languages.rust.categories.patterns' "$REPORT_JSON")
TS_PATTERNS=$(jq -r '.languages.typescript.categories.patterns' "$REPORT_JSON")

PYTHON_TECHNIQUES=$(jq -r '.languages.python.categories.techniques' "$REPORT_JSON")
GO_TECHNIQUES=$(jq -r '.languages.go.categories.techniques' "$REPORT_JSON")
CPP_TECHNIQUES=$(jq -r '.languages.cpp.categories.techniques' "$REPORT_JSON")
RUST_TECHNIQUES=$(jq -r '.languages.rust.categories.techniques' "$REPORT_JSON")
TS_TECHNIQUES_VAL=$(jq -r '.languages.typescript.categories.techniques' "$REPORT_JSON")

PYTHON_SAFETY=$(jq -r '.languages.python.categories.safety' "$REPORT_JSON")
GO_SAFETY=$(jq -r '.languages.go.categories.safety' "$REPORT_JSON")
RUST_SAFETY=$(jq -r '.languages.rust.categories.safety' "$REPORT_JSON")
TS_SAFETY_VAL=$(jq -r '.languages.typescript.categories.safety' "$REPORT_JSON")

PYTHON_ADAPTERS=$(jq -r '.languages.python.categories.adapters' "$REPORT_JSON")
GO_ADAPTERS=$(jq -r '.languages.go.categories.adapters' "$REPORT_JSON")
RUST_ADAPTERS=$(jq -r '.languages.rust.categories.adapters' "$REPORT_JSON")

PYTHON_EVALUATION=$(jq -r '.languages.python.categories.evaluation' "$REPORT_JSON")
GO_EVALUATION=$(jq -r '.languages.go.categories.evaluation' "$REPORT_JSON")
RUST_EVALUATION=$(jq -r '.languages.rust.categories.evaluation' "$REPORT_JSON")

PYTHON_MIDDLEWARE=$(jq -r '.languages.python.categories.middleware' "$REPORT_JSON")
GO_MIDDLEWARE=$(jq -r '.languages.go.categories.middleware' "$REPORT_JSON")

cat >> "$REPORT_MD" << MDCATDATA
| **Patterns** | $PYTHON_PATTERNS | $GO_PATTERNS ✅ | $CPP_PATTERNS ✅ | $RUST_PATTERNS ✅ | — | $TS_PATTERNS |
| **Techniques** | $PYTHON_TECHNIQUES | $GO_TECHNIQUES ❌ | $CPP_TECHNIQUES ❌ | $RUST_TECHNIQUES ❌ | — | $TS_TECHNIQUES_VAL ❌ |
| **Safety** | $PYTHON_SAFETY | $GO_SAFETY ❌ | 0 ❌ | $RUST_SAFETY ❌ | — | $TS_SAFETY_VAL ⚠️ |
| **Adapters** | $PYTHON_ADAPTERS | $GO_ADAPTERS ⚠️ | ~8 ❌ | $RUST_ADAPTERS ❌ | — | 0 ❌ |
| **Evaluation** | $PYTHON_EVALUATION | $GO_EVALUATION ⚠️ | — | $RUST_EVALUATION ⚠️ | — | 0 ❌ |
| **Middleware** | $PYTHON_MIDDLEWARE | $GO_MIDDLEWARE ⚠️ | — | — | — | — |

**Legend:** ✅ Good parity (>80%) | ⚠️ Partial (40-80%) | ❌ Missing (<40%) | — Not counted

### Advanced Categories (Nice to Have)

| Category | Python | Go | C++ | Rust | Zig | TypeScript |
|----------|--------|-----|-----|------|-----|------------|
MDCATDATA

PYTHON_ROUTING=$(jq -r '.languages.python.categories.routing' "$REPORT_JSON")
PYTHON_CHAOS=$(jq -r '.languages.python.categories.chaos' "$REPORT_JSON")
PYTHON_PROPERTY=$(jq -r '.languages.python.categories.property' "$REPORT_JSON")
PYTHON_BUDGET=$(jq -r '.languages.python.categories.budget' "$REPORT_JSON")
PYTHON_MEMORY=$(jq -r '.languages.python.categories.memory' "$REPORT_JSON")
GO_MEMORY=$(jq -r '.languages.go.categories.memory' "$REPORT_JSON")

cat >> "$REPORT_MD" << MDADV
| **Routing** | $PYTHON_ROUTING | 0 | — | — | — | — |
| **Chaos** | $PYTHON_CHAOS | 0 | — | — | — | — |
| **Property** | $PYTHON_PROPERTY | 0 | 0 | 0 | — | 0 |
| **Budget** | $PYTHON_BUDGET | ✅ | — | — | — | — |
| **Memory** | $PYTHON_MEMORY | $GO_MEMORY | — | — | — | — |

MDADV

# Add GitHub issues section
cat >> "$REPORT_MD" << 'MDISSUES'

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
| Go | GO_CURRENT | 1,500 | +GO_GAP | Techniques, Safety, Routing, Chaos |
| C++ | CPP_CURRENT | 1,500 | +CPP_GAP | Techniques, Safety, Adapters |
| Rust | RUST_CURRENT | 1,500 | +RUST_GAP | Techniques, Safety, Adapters |
| Zig | ZIG_CURRENT | 1,000 | +ZIG_GAP | Evaluation, Techniques |
| TypeScript | TS_CURRENT | 1,200 | +TS_GAP | Techniques, Safety, Adapters |

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
MDISSUES

# Replace placeholders with actual values
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed
    sed -i '' "s/GO_CURRENT/$GO_TOTAL_VAL/g" "$REPORT_MD"
    sed -i '' "s/CPP_CURRENT/$CPP_TOTAL_VAL/g" "$REPORT_MD"
    sed -i '' "s/RUST_CURRENT/$RUST_TOTAL_VAL/g" "$REPORT_MD"
    sed -i '' "s/ZIG_CURRENT/$ZIG_TOTAL_VAL/g" "$REPORT_MD"
    sed -i '' "s/TS_CURRENT/$TS_TOTAL_VAL/g" "$REPORT_MD"

    sed -i '' "s/GO_GAP/$((1500 - GO_TOTAL_VAL))/g" "$REPORT_MD"
    sed -i '' "s/CPP_GAP/$((1500 - CPP_TOTAL_VAL * 15))/g" "$REPORT_MD"
    sed -i '' "s/RUST_GAP/$((1500 - RUST_TOTAL_VAL))/g" "$REPORT_MD"
    sed -i '' "s/ZIG_GAP/$((1000 - ZIG_TOTAL_VAL))/g" "$REPORT_MD"
    sed -i '' "s/TS_GAP/$((1200 - TS_TOTAL_VAL))/g" "$REPORT_MD"
else
    # GNU sed
    sed -i "s/GO_CURRENT/$GO_TOTAL_VAL/g" "$REPORT_MD"
    sed -i "s/CPP_CURRENT/$CPP_TOTAL_VAL/g" "$REPORT_MD"
    sed -i "s/RUST_CURRENT/$RUST_TOTAL_VAL/g" "$REPORT_MD"
    sed -i "s/ZIG_CURRENT/$ZIG_TOTAL_VAL/g" "$REPORT_MD"
    sed -i "s/TS_CURRENT/$TS_TOTAL_VAL/g" "$REPORT_MD"

    sed -i "s/GO_GAP/$((1500 - GO_TOTAL_VAL))/g" "$REPORT_MD"
    sed -i "s/CPP_GAP/$((1500 - CPP_TOTAL_VAL * 15))/g" "$REPORT_MD"
    sed -i "s/RUST_GAP/$((1500 - RUST_TOTAL_VAL))/g" "$REPORT_MD"
    sed -i "s/ZIG_GAP/$((1000 - ZIG_TOTAL_VAL))/g" "$REPORT_MD"
    sed -i "s/TS_GAP/$((1200 - TS_TOTAL_VAL))/g" "$REPORT_MD"
fi

echo ""
echo "=== Report Generated ==="
echo "JSON: $REPORT_JSON"
echo "Markdown: $REPORT_MD"
echo ""
echo "View the dashboard: cat $REPORT_MD"
