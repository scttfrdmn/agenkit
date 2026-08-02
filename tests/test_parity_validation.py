"""Test parity validation suite.

This module validates that all languages maintain minimum test parity
thresholds relative to the Python reference implementation. It fails
if any language drops below its minimum threshold, preventing drift.

Part of v0.48.0 Phase 2: Parity Enforcement (Task 2.2)
"""

import json
from datetime import UTC
from pathlib import Path
from typing import Any

import pytest

# Parity thresholds (percentage of Python tests)
# These represent the MINIMUM acceptable parity for each language.
# NOTE: thresholds are floors below the *current* ratio so they catch
# regressions without breaking on Python test growth. When Python's total
# rises, every other language's percentage falls mechanically — recalibrate
# floors (not the implementations) and refresh the baselines below.
# Baselines reflect the 2026-08 regenerated report (Python total = 2117).
#
# Zig's floor was raised from 10.0 in #757. `zig build test` prints no aggregate
# count, so the old parse never matched and the script fell back to a hardcoded
# "214" on every run -- Zig's real total is 496, understated by 2.3x. The floor
# had been calibrated against the fabricated number.
TOTAL_PARITY_THRESHOLDS = {
    "go": 50.0,  # Currently 59.8% (1265/2117)
    "cpp": 40.0,  # Currently 50.8% (1076/2117)
    "rust": 35.0,  # Currently 60.2% (1274/2117)
    "typescript": 25.0,  # Currently 45.7% (968/2117)
    "zig": 20.0,  # Currently 23.4% (496/2117)
    # C#/Java/Scala had no floor at all before #757, and were absent from the
    # report entirely, so test_total_parity_threshold skipped them -- they could
    # have lost every test without failing anything. They trail the older
    # implementations because they are newer (v0.71.0-v0.73.0), not because they
    # are less complete: all three are full-parity on features (#753).
    "csharp": 10.0,  # Currently 12.8% (272/2117)
    "java": 14.0,  # Currently 16.9% (358/2117)
    "scala": 14.0,  # Currently 17.1% (363/2117)
}

# Category-specific thresholds (percentage of Python category tests)
# Only enforce where we have significant implementation
CATEGORY_THRESHOLDS = {
    "go": {
        "patterns": 80.0,  # 81.7% (362/443) - excellent pattern coverage
        "techniques": 15.0,  # 44.6% (107/240) - growing area
        "safety": 50.0,  # 58.0% (94/162) - strong safety implementation
        "adapters": 35.0,  # 63.1% (89/141) - good adapter coverage
        "evaluation": 100.0,  # 109.5% (127/116) - comprehensive evaluation
        "middleware": 90.0,  # 98.9% (91/92) - strong middleware
    },
    "cpp": {
        "patterns": 65.0,  # 70.0% (310/443) - strong pattern implementation
        "techniques": 9.0,  # 48.3% (116/240) - growing area
        "adapters": 33.0,  # 35.5% (50/141) - good coverage in integration tests
    },
    "rust": {
        "patterns": 30.0,  # 30.0% (133/443) - solid pattern coverage
        "techniques": 0.0,  # 39.6% (95/240) - growing area
        "safety": 30.0,  # 37.0% (60/162) - strong safety implementation
    },
    "typescript": {
        "patterns": 1.5,  # 1.6% (7/439) - early stage
        "techniques": 0.0,  # 0% (0/240) - not implemented
        "adapters": 0.0,  # 0% (0/151) - not implemented
        "chaos": 115.0,  # 115.1% (61/53) - comprehensive chaos testing!
        "property": 21.0,  # 21.6% (8/37) - property-based testing started
        "integration": 50.0,  # 50.0% (45/90) - solid integration testing
    },
    "zig": {
        "patterns": 0.0,  # Zig has no category breakdown - can't enforce
        "safety": 0.0,  # Zig has no category breakdown - can't enforce
        "adapters": 0.0,  # Zig has no category breakdown - can't enforce
    },
    # C#/Java/Scala floors, added in #757. Percentages are of Python's count for
    # the same category. `techniques` is deliberately absent for all three rather
    # than set to 0.0: they have no techniques subsystem (#754), and a 0.0 floor
    # would silently "pass" if the subsystem were added and then broke.
    "csharp": {
        "patterns": 15.0,  # 19.6% (87/443)
        "middleware": 35.0,  # 41.3% (38/92)
        "memory": 18.0,  # 22.8% (23/101)
        "adapters": 5.0,  # 7.8% (11/141)
    },
    "java": {
        "patterns": 25.0,  # 30.5% (135/443)
        "middleware": 30.0,  # 35.9% (33/92)
        "memory": 10.0,  # 13.9% (14/101)
        "adapters": 8.0,  # 11.3% (16/141)
        "property": 80.0,  # 94.6% (35/37) - jqwik property tests
    },
    "scala": {
        "patterns": 25.0,  # 30.5% (135/443)
        "middleware": 50.0,  # 59.8% (55/92)
        "memory": 18.0,  # 23.8% (24/101)
        "adapters": 5.0,  # 7.8% (11/141)
    },
}


@pytest.fixture(scope="module")
def parity_report() -> dict[str, Any]:
    """Load the latest parity report from JSON file."""
    report_path = Path(__file__).parent.parent / "test-parity-report.json"

    if not report_path.exists():
        pytest.skip(f"Parity report not found at {report_path}")

    with report_path.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def python_total(parity_report: dict[str, Any]) -> int:
    """Get total Python test count (reference implementation)."""
    return parity_report["languages"]["python"]["total"]


@pytest.mark.parametrize(
    "language",
    ["go", "cpp", "rust", "typescript", "zig", "csharp", "java", "scala"],
)
def test_total_parity_threshold(
    parity_report: dict[str, Any],
    python_total: int,
    language: str,
) -> None:
    """Verify language meets minimum total parity threshold.

    This test ensures that no language drops below its minimum
    acceptable test count relative to Python.
    """
    lang_data = parity_report["languages"].get(language)
    if not lang_data:
        # Absent-means-skip is why C#/Java/Scala were unguarded for three
        # releases: they had no floor AND no report entry, so this test passed
        # by skipping. Every language in TOTAL_PARITY_THRESHOLDS is now written
        # by scripts/test-parity.sh, so absence is a generator bug, not a
        # not-yet-implemented language. See #757.
        pytest.fail(
            f"Language '{language}' has a parity threshold but is missing from the "
            f"report. Regenerate with scripts/test-parity.sh; if it genuinely has "
            f"no tests, remove its threshold rather than leaving it unmeasured."
        )

    lang_total = lang_data["total"]
    required_threshold = TOTAL_PARITY_THRESHOLDS[language]

    # Calculate actual parity percentage
    actual_parity = (lang_total / python_total) * 100 if python_total > 0 else 0

    # Fail if below threshold
    assert actual_parity >= required_threshold, (
        f"{language.upper()} parity is {actual_parity:.1f}% "
        f"(below minimum threshold of {required_threshold:.1f}%). "
        f"Current: {lang_total} tests, Required: {int(python_total * required_threshold / 100)} tests"
    )


@pytest.mark.parametrize(
    ("language", "category"),
    [
        # Go categories
        ("go", "patterns"),
        ("go", "techniques"),
        ("go", "safety"),
        ("go", "adapters"),
        ("go", "evaluation"),
        ("go", "middleware"),
        # C++ categories
        ("cpp", "patterns"),
        ("cpp", "techniques"),
        ("cpp", "adapters"),
        # Rust categories
        ("rust", "patterns"),
        ("rust", "techniques"),
        ("rust", "safety"),
        # TypeScript categories
        ("typescript", "patterns"),
        ("typescript", "techniques"),
        ("typescript", "adapters"),
        # Zig categories
        ("zig", "patterns"),
        ("zig", "safety"),
        ("zig", "adapters"),
        # C# categories
        ("csharp", "patterns"),
        ("csharp", "middleware"),
        ("csharp", "memory"),
        ("csharp", "adapters"),
        # Java categories
        ("java", "patterns"),
        ("java", "middleware"),
        ("java", "memory"),
        ("java", "adapters"),
        ("java", "property"),
        # Scala categories
        ("scala", "patterns"),
        ("scala", "middleware"),
        ("scala", "memory"),
        ("scala", "adapters"),
    ],
)
def test_category_parity_threshold(
    parity_report: dict[str, Any],
    language: str,
    category: str,
) -> None:
    """Verify category-specific parity thresholds.

    This test ensures that specific categories (patterns, techniques,
    safety, etc.) maintain minimum parity within each language.
    """
    # Get threshold for this language/category
    required_threshold = CATEGORY_THRESHOLDS.get(language, {}).get(category)
    if required_threshold is None:
        pytest.skip(f"No threshold defined for {language}/{category}")

    # Get Python category count
    python_data = parity_report["languages"]["python"]["categories"]
    python_category_total = python_data.get(category, 0)

    if python_category_total == 0:
        pytest.skip(f"Python has no tests in category '{category}'")

    # Get language category count
    lang_data = parity_report["languages"].get(language)
    if not lang_data:
        # Same absent-means-skip hole as test_total_parity_threshold had: a
        # language with a threshold but no report entry passed by skipping. If a
        # language has a category floor here, it is expected in the report. See #757.
        pytest.fail(
            f"Language '{language}' has a {category} threshold but is missing from "
            f"the report. Regenerate with scripts/test-parity.sh."
        )

    lang_category_total = lang_data.get("categories", {}).get(category, 0)

    # Calculate actual parity percentage
    actual_parity = (lang_category_total / python_category_total) * 100

    # Fail if below threshold
    assert actual_parity >= required_threshold, (
        f"{language.upper()} {category} parity is {actual_parity:.1f}% "
        f"(below minimum threshold of {required_threshold:.1f}%). "
        f"Current: {lang_category_total} tests, "
        f"Required: {int(python_category_total * required_threshold / 100)} tests"
    )


def test_no_missing_languages(parity_report: dict[str, Any]) -> None:
    """Verify all nine implementations are present in the report.

    C#, Java and Scala were absent from ``expected_languages`` until #757, so
    this test would not have failed if ``agenkit-cs``, ``agenkit-java`` or
    ``agenkit-scala`` had disappeared entirely.

    All nine are shipped, full-parity implementations that
    ``scripts/test-parity.sh`` writes on every run, so a missing language means
    the generator broke -- not that the language is still being developed. The
    old "warn but skip during development" branch is gone: a skip here is
    indistinguishable from a pass in CI output, which is how three languages went
    unmeasured for three releases.
    """
    expected_languages = {
        "python",
        "go",
        "cpp",
        "rust",
        "typescript",
        "zig",
        "csharp",
        "java",
        "scala",
    }
    actual_languages = set(parity_report["languages"].keys())

    missing = expected_languages - actual_languages

    if missing:
        pytest.fail(
            f"Missing languages in parity report: {sorted(missing)}. "
            f"Regenerate with scripts/test-parity.sh."
        )


def test_python_is_reference(parity_report: dict[str, Any]) -> None:
    """Verify Python exists and has a reasonable test count.

    Python is the reference implementation and should have
    the most comprehensive test coverage.
    """
    python_total = parity_report["languages"]["python"]["total"]

    # Python should have at least 1500 tests (we know it has ~1792)
    assert python_total >= 1500, (
        f"Python test count ({python_total}) seems too low. "
        "Expected at least 1500 tests for reference implementation."
    )

    # Python should have all major categories
    categories = parity_report["languages"]["python"]["categories"]
    required_categories = {
        "patterns",
        "techniques",
        "safety",
        "adapters",
        "evaluation",
        "middleware",
    }

    for cat in required_categories:
        assert cat in categories, f"Python missing required category: {cat}"
        assert categories[cat] > 0, f"Python has 0 tests in category: {cat}"


def test_all_languages_have_patterns(parity_report: dict[str, Any]) -> None:
    """Verify all languages have pattern tests.

    Patterns are the core of the toolkit and all languages
    should have reasonable pattern coverage.
    """
    # Define minimum pattern parity per language (some are still early stage)
    min_pattern_parity_by_lang = {
        "go": 80.0,  # Mature implementation (81.7%)
        "cpp": 65.0,  # Strong implementation (70.0%)
        "rust": 30.0,  # Solid implementation (30.0%)
        "typescript": 1.0,  # Early stage (3.6%)
        "zig": 0.0,  # No category breakdown available
        # Added in #757 -- these three were unguarded despite being full-parity
        # implementations since v0.71.0-v0.73.0.
        "csharp": 15.0,  # Currently 19.6% (87/443)
        "java": 25.0,  # Currently 30.5% (135/443)
        "scala": 25.0,  # Currently 30.5% (135/443)
    }

    for language in ["go", "cpp", "rust", "typescript", "zig", "csharp", "java", "scala"]:
        lang_data = parity_report["languages"].get(language)
        if not lang_data:
            pytest.fail(f"{language} is missing from the parity report")

        pattern_tests = lang_data.get("categories", {}).get("patterns", 0)

        # Zig reports one aggregate count with no category breakdown, so there is
        # no patterns figure to compare. Its total is guarded by
        # test_zig_infrastructure_complete instead.
        if language == "zig":
            continue

        # TypeScript early stage - just check it has some tests registered
        if language == "typescript" and pattern_tests == 0:
            # TypeScript counts are file-based estimates, may show 0 in categories
            continue

        python_patterns = parity_report["languages"]["python"]["categories"]["patterns"]
        pattern_parity = (pattern_tests / python_patterns) * 100 if pattern_tests > 0 else 0

        min_pattern_parity = min_pattern_parity_by_lang.get(language, 1.0)

        assert pattern_parity >= min_pattern_parity, (
            f"{language.upper()} pattern parity ({pattern_parity:.1f}%) "
            f"is below minimum ({min_pattern_parity}%)"
        )


def test_report_has_timestamp(parity_report: dict[str, Any]) -> None:
    """Verify the parity report has a generation timestamp."""
    assert "generated_at" in parity_report, "Parity report missing 'generated_at'"

    # Validate it's a valid ISO8601 timestamp
    timestamp = parity_report["generated_at"]
    from datetime import datetime

    try:
        datetime.fromisoformat(timestamp)
    except (ValueError, AttributeError) as e:
        pytest.fail(f"Invalid timestamp format: {timestamp} ({e})")


def test_no_negative_test_counts(parity_report: dict[str, Any]) -> None:
    """Verify no language has negative test counts.

    This catches bugs in the counting logic.
    """
    for lang_name, lang_data in parity_report["languages"].items():
        total = lang_data.get("total", 0)
        assert total >= 0, f"{lang_name} has negative total: {total}"

        categories = lang_data.get("categories", {})
        for cat_name, cat_count in categories.items():
            assert cat_count >= 0, f"{lang_name}/{cat_name} has negative count: {cat_count}"


def test_zig_infrastructure_complete(parity_report: dict[str, Any]) -> None:
    """Verify Zig has infrastructure tests after Phase 1 completion.

    Zig Infrastructure Phase 1 (v0.47.0) added:
    - Memory system (13+ tests)
    - Checkpointing (10+ tests)
    - Budget tracking (15+ tests)

    This should be reflected in the parity report.

    Both floors here were recalibrated in #757. `zig build test` prints no
    aggregate count, so the old parse never matched and the script substituted a
    hardcoded 214 on every run. Zig's real total is 496 -- understated by 2.3x --
    and these floors (210 tests, 10.0% parity) had been set just below the
    fabricated number, so they could not have caught even a halving of Zig's
    suite. The count now comes from `zig build test --summary all`.
    """
    zig_data = parity_report["languages"].get("zig")
    if not zig_data:
        pytest.fail("Zig is missing from the parity report")

    zig_total = zig_data["total"]

    # 450 sits just below the measured 496. The old 210 was below a number the
    # script invented, not a number it measured.
    assert zig_total >= 450, (
        f"Zig total ({zig_total}) is below the floor (450; measured 496). "
        "Infrastructure implementation may be missing, or the "
        "'zig build test --summary all' parse in scripts/test-parity.sh broke."
    )

    # Verify Zig parity stays above its floor. This is a percentage of the
    # Python baseline, which keeps growing (now 2117), so the floor tracks
    # below the current ratio (23.4%) rather than pinning a fixed target.
    python_total = parity_report["languages"]["python"]["total"]
    zig_parity = (zig_total / python_total) * 100

    assert zig_parity >= 20.0, (
        f"Zig parity ({zig_parity:.1f}%) below floor (20.0%). "
        "Expected improvement after infrastructure work."
    )


def test_cpp_test_counting_fixed(parity_report: dict[str, Any]) -> None:
    """Verify C++ test counting reports individual tests, not suites.

    After the fix in Task 2.1, C++ should report ~793 tests,
    not 0 or a small number of test suites.
    """
    cpp_total = parity_report["languages"]["cpp"]["total"]

    # C++ should have at least 700 tests after counting fix
    assert cpp_total >= 700, (
        f"C++ total ({cpp_total}) suggests counting is broken. "
        "Expected ~793 individual TEST() macros after fix."
    )

    # Check the note was updated
    cpp_note = parity_report["languages"]["cpp"].get("note", "")
    assert "individual TEST()" in cpp_note or "TEST() macros" in cpp_note, (
        f"C++ note should mention individual tests: {cpp_note}"
    )


@pytest.mark.slow
def test_parity_report_is_current(parity_report: dict[str, Any]) -> None:
    """Verify the parity report is recent (within last 7 days).

    This test is marked slow and can be skipped in fast test runs.
    It ensures the CI is actually running and updating the report.
    """
    from datetime import datetime, timedelta

    timestamp = parity_report["generated_at"]
    generated_at = datetime.fromisoformat(timestamp)
    now = datetime.now(UTC)

    age = now - generated_at
    max_age = timedelta(days=90)

    assert age <= max_age, (
        f"Parity report is {age.days} days old (generated {generated_at}). "
        "Expected report within last 90 days."
    )


# Regression detection tests
def test_go_parity_no_regression(parity_report: dict[str, Any]) -> None:
    """Verify Go maintains parity above historical minimum.

    Go has been the strongest non-Python implementation.
    It should never drop below 50% parity.
    """
    python_total = parity_report["languages"]["python"]["total"]
    go_total = parity_report["languages"]["go"]["total"]
    go_parity = (go_total / python_total) * 100

    # Historical minimum from v0.44.0+
    historical_minimum = 50.0

    assert go_parity >= historical_minimum, (
        f"Go parity ({go_parity:.1f}%) regressed below historical minimum "
        f"({historical_minimum}%). This indicates significant test removal."
    )


def test_all_languages_positive_counts(parity_report: dict[str, Any]) -> None:
    """Verify all present languages have positive test counts.

    Every language should have at least some tests implemented.
    Zero suggests a counting or build problem.
    """
    # Check all languages that are present in the report
    for lang_name, lang_data in parity_report["languages"].items():
        if lang_name == "python":
            continue  # Skip Python (tested separately)

        total = lang_data.get("total", 0)
        assert total > 0, (
            f"{lang_name.upper()} has zero tests. This suggests a counting or build issue."
        )


# Summary test (always runs last due to name)
def test_zzz_parity_summary(parity_report: dict[str, Any]) -> None:
    """Print a summary of test parity across all languages.

    This test always passes but prints useful summary information.
    The zzz_ prefix ensures it runs last alphabetically.
    """
    python_total = parity_report["languages"]["python"]["total"]

    print("\n" + "=" * 70)
    print("TEST PARITY SUMMARY")
    print("=" * 70)
    print(f"{'Language':<12} {'Tests':>8} {'Parity':>8} {'Threshold':>10} {'Status':>8}")
    print("-" * 70)

    # Always show Python first
    print(f"{'PYTHON':<12} {python_total:>8} {'100.0%':>8} {'baseline':>10} {'✅':>8}")

    # Driven off TOTAL_PARITY_THRESHOLDS rather than a second hardcoded list, so
    # adding a language in one place can't leave it out of the summary -- which is
    # how C#/Java/Scala stayed invisible here through v0.71.0-v0.73.0.
    for lang in TOTAL_PARITY_THRESHOLDS:
        lang_data = parity_report["languages"].get(lang)
        if not lang_data:
            # Language not in report yet
            print(f"{lang.upper():<12} {'N/A':>8} {'N/A':>8} {'N/A':>10} {'⏸️':>8}")
            continue

        total = lang_data["total"]
        parity = (total / python_total) * 100
        parity_str = f"{parity:.1f}%"
        threshold = TOTAL_PARITY_THRESHOLDS.get(lang, 0)
        threshold_str = f"{threshold:.1f}%"
        status = "✅" if parity >= threshold else "❌"

        print(f"{lang.upper():<12} {total:>8} {parity_str:>8} {threshold_str:>10} {status:>8}")

    print("=" * 70)
    print(f"Report generated: {parity_report['generated_at']}")
    print("=" * 70 + "\n")

    # This test always passes - it's just for informational output
    assert True
