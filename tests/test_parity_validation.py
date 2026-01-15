"""Test parity validation suite.

This module validates that all languages maintain minimum test parity
thresholds relative to the Python reference implementation. It fails
if any language drops below its minimum threshold, preventing drift.

Part of v0.48.0 Phase 2: Parity Enforcement (Task 2.2)
"""

import json
from pathlib import Path
from typing import Any

import pytest


# Parity thresholds (percentage of Python tests)
# These represent the MINIMUM acceptable parity for each language
TOTAL_PARITY_THRESHOLDS = {
    "go": 50.0,  # Currently 53.0%
    "cpp": 40.0,  # Currently 44.3%
    "rust": 15.0,  # Currently 15.4%
    "typescript": 18.0,  # Currently 18.3%
    "zig": 13.0,  # Currently 13.7%
}

# Category-specific thresholds (percentage of Python category tests)
# Only enforce where we have significant implementation
CATEGORY_THRESHOLDS = {
    "go": {
        "patterns": 80.0,  # Go has excellent pattern coverage
        "techniques": 15.0,  # Growing area
        "safety": 50.0,  # Strong safety implementation
        "adapters": 35.0,  # Good adapter coverage
        "evaluation": 100.0,  # Go evaluation is comprehensive
        "middleware": 90.0,  # Strong middleware
    },
    "cpp": {
        "patterns": 70.0,  # Strong pattern implementation
        "techniques": 9.0,  # Early stages
        "adapters": 35.0,  # Good coverage in integration tests
    },
    "rust": {
        "patterns": 70.0,  # Rust has good pattern coverage
        "techniques": 15.0,  # Growing
        "safety": 50.0,  # Rust emphasizes safety
    },
    "typescript": {
        "patterns": 70.0,  # TypeScript has solid patterns
        "techniques": 15.0,  # Growing area
        "adapters": 35.0,  # Good adapter coverage
    },
    "zig": {
        "patterns": 60.0,  # Zig patterns developing
        "safety": 30.0,  # Basic safety coverage
        "adapters": 35.0,  # Adapter work in progress
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
    ["go", "cpp", "rust", "typescript", "zig"],
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
        pytest.skip(f"Language '{language}' not found in parity report (may not be generated yet)")

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
        pytest.skip(f"Language '{language}' not found in parity report (may not be generated yet)")

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
    """Verify all expected languages are present in the report.

    In CI, all languages must be present. During development, we warn
    if languages are missing but don't fail the test.
    """
    expected_languages = {"python", "go", "cpp", "rust", "typescript", "zig"}
    actual_languages = set(parity_report["languages"].keys())

    missing = expected_languages - actual_languages

    # Always require Python, Go, and C++ (core languages)
    required_languages = {"python", "go", "cpp"}
    missing_required = missing & required_languages

    if missing_required:
        pytest.fail(f"Missing required languages in parity report: {missing_required}")

    # Warn about other missing languages but don't fail
    if missing:
        pytest.skip(f"Some languages not yet in parity report: {missing}. This is OK during development.")


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
    for language in ["go", "cpp", "rust", "typescript", "zig"]:
        lang_data = parity_report["languages"].get(language)
        if not lang_data:
            continue

        pattern_tests = lang_data.get("categories", {}).get("patterns", 0)
        assert pattern_tests > 0, f"{language.upper()} has no pattern tests"

        # All languages should have at least 50% pattern parity
        python_patterns = parity_report["languages"]["python"]["categories"][
            "patterns"
        ]
        pattern_parity = (pattern_tests / python_patterns) * 100

        # More lenient for Zig (newer), stricter for others
        min_pattern_parity = 50.0 if language != "zig" else 40.0

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
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
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
            assert cat_count >= 0, (
                f"{lang_name}/{cat_name} has negative count: {cat_count}"
            )


def test_zig_infrastructure_complete(parity_report: dict[str, Any]) -> None:
    """Verify Zig has infrastructure tests after Phase 1 completion.

    Zig Infrastructure Phase 1 (v0.47.0) added:
    - Memory system (13+ tests)
    - Checkpointing (10+ tests)
    - Budget tracking (15+ tests)

    This should be reflected in the parity report.
    """
    zig_data = parity_report["languages"].get("zig")
    if not zig_data:
        pytest.skip("Zig not in parity report yet")

    zig_total = zig_data["total"]

    # After Phase 1, Zig should have at least 245 tests (13.7% parity)
    assert zig_total >= 245, (
        f"Zig total ({zig_total}) is below Phase 1 completion count (245). "
        "Infrastructure implementation may be missing."
    )

    # Verify Zig parity improved from 11.9% to at least 13%
    python_total = parity_report["languages"]["python"]["total"]
    zig_parity = (zig_total / python_total) * 100

    assert zig_parity >= 13.0, (
        f"Zig parity ({zig_parity:.1f}%) below Phase 1 target (13.0%). "
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
    from datetime import datetime, timedelta, timezone

    timestamp = parity_report["generated_at"]
    generated_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    age = now - generated_at
    max_age = timedelta(days=7)

    assert age <= max_age, (
        f"Parity report is {age.days} days old (generated {generated_at}). "
        "CI may not be running. Expected report within last 7 days."
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
            f"{lang_name.upper()} has zero tests. "
            "This suggests a counting or build issue."
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

    # Show all other languages that are present
    for lang in ["go", "cpp", "rust", "typescript", "zig"]:
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
