"""
Tests for benchmark suites.

Tests SimpleQA, NeedleInHaystack, ExtremeScale, and BenchmarkSuite.
"""

import pytest
from agenkit.evaluation.benchmarks import (
    SimpleQABenchmark,
    NeedleInHaystackBenchmark,
    ExtremeScaleBenchmark,
    InformationRetentionBenchmark,
    BenchmarkSuite
)


@pytest.mark.asyncio
async def test_simple_qa_benchmark():
    """Test simple Q&A benchmark generation."""
    benchmark = SimpleQABenchmark()

    assert benchmark.name == "simple_qa"
    assert "question-answering" in benchmark.description.lower()

    test_cases = await benchmark.generate_test_cases()

    assert len(test_cases) > 0
    assert all(hasattr(tc, "input") for tc in test_cases)
    assert all(hasattr(tc, "expected") for tc in test_cases)
    assert all(hasattr(tc, "tags") for tc in test_cases)


@pytest.mark.asyncio
async def test_needle_in_haystack_benchmark():
    """Test needle-in-haystack benchmark generation."""
    benchmark = NeedleInHaystackBenchmark(
        context_length=1000,
        needle_count=3
    )

    assert benchmark.name == "needle_in_haystack_1000"
    assert "1000" in benchmark.description

    test_cases = await benchmark.generate_test_cases()

    assert len(test_cases) == 3  # One test per needle
    assert all("retrieval" in tc.tags for tc in test_cases)
    assert all("context" in tc.tags for tc in test_cases)


@pytest.mark.asyncio
async def test_needle_haystack_embedding():
    """Test that needles are properly embedded in haystack."""
    benchmark = NeedleInHaystackBenchmark(
        context_length=1000,
        needle_count=2
    )

    test_cases = await benchmark.generate_test_cases()

    # Check that expected value appears in input
    for tc in test_cases:
        assert tc.expected in tc.input


@pytest.mark.asyncio
async def test_extreme_scale_benchmark():
    """Test extreme-scale benchmark generation."""
    benchmark = ExtremeScaleBenchmark(
        test_lengths=[10_000, 100_000],
        needles_per_length=2
    )

    assert benchmark.name == "extreme_scale"
    assert "retrieval" in benchmark.description.lower()

    test_cases = await benchmark.generate_test_cases()

    # 2 lengths * 2 needles = 4 test cases
    assert len(test_cases) == 4
    assert all("extreme_scale" in tc.tags for tc in test_cases)


@pytest.mark.asyncio
async def test_information_retention_benchmark():
    """Test information retention benchmark."""
    benchmark = InformationRetentionBenchmark(
        conversation_length=100,  # Long enough to have plant events
        recall_points=[25, 50, 75]
    )

    assert benchmark.name == "information_retention"
    assert "recall" in benchmark.description.lower()

    test_cases = await benchmark.generate_test_cases()

    # Should have plant, filler, and recall test cases
    assert len(test_cases) > 0

    # Check types
    plant_cases = [tc for tc in test_cases if tc.metadata.get("type") == "fact_plant"]
    recall_cases = [tc for tc in test_cases if tc.metadata.get("type") == "recall_test"]

    assert len(plant_cases) > 0
    assert len(recall_cases) > 0


@pytest.mark.asyncio
async def test_benchmark_suite_standard():
    """Test standard benchmark suite."""
    suite = BenchmarkSuite.standard()

    assert suite.suite_name == "standard"
    assert len(suite.benchmarks) > 0

    test_cases = await suite.generate_all_test_cases()

    assert len(test_cases) > 0
    assert all(tc.metadata.get("suite_name") == "standard" for tc in test_cases)


@pytest.mark.asyncio
async def test_benchmark_suite_extreme_scale():
    """Test extreme-scale benchmark suite."""
    suite = BenchmarkSuite.extreme_scale()

    assert suite.suite_name == "extreme_scale"
    assert len(suite.benchmarks) > 0

    # Just verify structure (don't generate all test cases - too large)
    assert suite.get_benchmark("extreme_scale") is not None


@pytest.mark.asyncio
async def test_benchmark_suite_quick():
    """Test quick benchmark suite."""
    suite = BenchmarkSuite.quick()

    assert suite.suite_name == "quick"
    assert len(suite.benchmarks) > 0

    test_cases = await suite.generate_all_test_cases()

    # Quick suite should have fewer test cases
    assert len(test_cases) > 0
    assert len(test_cases) < 100  # Reasonable quick test count


@pytest.mark.asyncio
async def test_benchmark_suite_get_benchmark():
    """Test getting benchmark by name."""
    suite = BenchmarkSuite.standard()

    benchmark = suite.get_benchmark("simple_qa")
    assert benchmark is not None
    assert benchmark.name == "simple_qa"

    missing = suite.get_benchmark("nonexistent")
    assert missing is None


@pytest.mark.asyncio
async def test_benchmark_suite_add_remove():
    """Test adding and removing benchmarks."""
    suite = BenchmarkSuite(name="custom")

    # Add benchmark
    benchmark = SimpleQABenchmark()
    suite.add_benchmark(benchmark)

    assert len(suite.benchmarks) == 1
    assert suite.get_benchmark("simple_qa") is not None

    # Remove benchmark
    suite.remove_benchmark("simple_qa")

    assert len(suite.benchmarks) == 0
    assert suite.get_benchmark("simple_qa") is None


@pytest.mark.asyncio
async def test_benchmark_suite_to_dict():
    """Test benchmark suite serialization."""
    suite = BenchmarkSuite.quick()

    data = suite.to_dict()

    assert data["suite_name"] == "quick"
    assert "benchmarks" in data
    assert len(data["benchmarks"]) > 0
    assert all("name" in b for b in data["benchmarks"])
    assert all("description" in b for b in data["benchmarks"])


@pytest.mark.asyncio
async def test_test_case_to_dict():
    """Test TestCase serialization."""
    benchmark = SimpleQABenchmark()
    test_cases = await benchmark.generate_test_cases()

    tc = test_cases[0]
    data = tc.to_dict()

    assert "input" in data
    assert "expected" in data
    assert "metadata" in data
    assert "tags" in data
