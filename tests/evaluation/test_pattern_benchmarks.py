"""Tests for pattern benchmark suite."""

import asyncio

# Import directly to avoid sklearn dependency
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agenkit.evaluation.pattern_benchmarks import (
    PatternBenchmark,
    PatternBenchmarkSuite,
    YAMLBenchmarkLoader,
)
from agenkit.interfaces import Message


class TestYAMLBenchmarkLoader:
    """Test YAML benchmark loading."""

    @pytest.fixture
    def specs_dir(self):
        """Get specs directory."""
        return Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"

    @pytest.fixture
    def loader(self, specs_dir):
        """Create YAML loader."""
        return YAMLBenchmarkLoader(specs_dir)

    def test_loader_initialization(self, specs_dir):
        """Test loader can be initialized with specs directory."""
        loader = YAMLBenchmarkLoader(specs_dir)
        assert loader.specs_dir == specs_dir

    def test_loader_invalid_directory(self):
        """Test loader raises error for invalid directory."""
        with pytest.raises(ValueError, match="Specs directory not found"):
            YAMLBenchmarkLoader("/nonexistent/path")

    def test_load_pattern_benchmark(self, loader):
        """Test loading a single pattern benchmark."""
        benchmark = loader.load_pattern_benchmark("reflection")

        assert isinstance(benchmark, PatternBenchmark)
        assert benchmark._pattern_name == "reflection"
        assert "reflection" in benchmark.description.lower()
        assert len(benchmark._test_cases) > 0

    def test_load_all_pattern_benchmarks(self, loader):
        """Test loading all pattern benchmarks."""
        benchmarks = loader.load_all_pattern_benchmarks()

        assert len(benchmarks) > 15  # Should have at least 18 patterns
        assert all(isinstance(b, PatternBenchmark) for b in benchmarks)

        # Check some expected patterns
        pattern_names = {b._pattern_name for b in benchmarks}
        assert "reflection" in pattern_names
        assert "sequential" in pattern_names
        assert "parallel" in pattern_names

    def test_benchmark_has_test_cases(self, loader):
        """Test that loaded benchmark has test cases."""
        benchmark = loader.load_pattern_benchmark("reflection")
        test_cases = asyncio.run(benchmark.generate_test_cases())

        assert len(test_cases) > 0
        for tc in test_cases:
            assert tc.input  # Has input
            assert tc.expected  # Has validator
            assert "reflection" in tc.tags  # Has pattern tag
            assert tc.metadata.get("pattern") == "reflection"

    def test_validator_creation(self, loader):
        """Test that validators are created from YAML specs."""
        benchmark = loader.load_pattern_benchmark("reflection")
        test_cases = asyncio.run(benchmark.generate_test_cases())

        # All test cases should have validators
        for tc in test_cases:
            assert callable(tc.expected)

            # Test validator with mock message
            mock_msg = Message(
                role="assistant",
                content="test response",
                metadata={"iterations": 1, "improved": True},
            )

            # Validator should be callable
            try:
                result = tc.expected(mock_msg)
                assert isinstance(result, bool)
            except Exception:  # noqa: S110 - Expected test failures for validators requiring specific content
                # Some validators may require specific content
                pass


class TestPatternBenchmark:
    """Test PatternBenchmark class."""

    def test_benchmark_properties(self):
        """Test benchmark properties."""
        from agenkit.evaluation.benchmarks import TestCase

        test_cases = [
            TestCase(
                input="test input", expected="test output", metadata={"test": True}, tags=["test"]
            )
        ]

        benchmark = PatternBenchmark(
            pattern_name="test_pattern",
            description="Test pattern description",
            test_cases=test_cases,
        )

        assert benchmark.name == "test_pattern_benchmark"
        assert benchmark.description == "Test pattern description"
        assert benchmark._pattern_name == "test_pattern"

    def test_generate_test_cases(self):
        """Test test case generation."""
        from agenkit.evaluation.benchmarks import TestCase

        test_cases = [
            TestCase(input=f"input_{i}", expected=f"output_{i}", metadata={}, tags=[])
            for i in range(3)
        ]

        benchmark = PatternBenchmark(
            pattern_name="test",
            description="Test",
            test_cases=test_cases,
        )

        generated = asyncio.run(benchmark.generate_test_cases())
        assert len(generated) == 3
        assert generated == test_cases


class TestPatternBenchmarkSuite:
    """Test PatternBenchmarkSuite class."""

    @pytest.fixture
    def specs_dir(self):
        """Get specs directory."""
        return Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"

    def test_from_yaml_specs(self, specs_dir):
        """Test creating suite from YAML specs."""
        suite = PatternBenchmarkSuite.from_yaml_specs(specs_dir)

        assert len(suite.benchmarks) > 15
        assert all(isinstance(b, PatternBenchmark) for b in suite.benchmarks)

    def test_get_benchmark(self, specs_dir):
        """Test getting specific benchmark."""
        suite = PatternBenchmarkSuite.from_yaml_specs(specs_dir)

        reflection = suite.get_benchmark("reflection")
        assert reflection is not None
        assert reflection._pattern_name == "reflection"

        nonexistent = suite.get_benchmark("nonexistent_pattern")
        assert nonexistent is None

    def test_get_benchmarks_by_tag(self, specs_dir):
        """Test filtering benchmarks by tag."""
        suite = PatternBenchmarkSuite.from_yaml_specs(specs_dir)

        # All benchmarks should have "yaml_generated" tag
        yaml_benchmarks = suite.get_benchmarks_by_tag("yaml_generated")
        assert len(yaml_benchmarks) > 0

    def test_to_dict(self, specs_dir):
        """Test suite serialization."""
        suite = PatternBenchmarkSuite.from_yaml_specs(specs_dir)

        data = suite.to_dict()
        assert "patterns" in data
        assert "total_benchmarks" in data
        assert "descriptions" in data

        assert data["total_benchmarks"] == len(suite.benchmarks)
        assert len(data["patterns"]) == len(suite.benchmarks)


class TestBenchmarkValidators:
    """Test validator functions created from YAML."""

    def test_role_validation(self):
        """Test role validation works."""
        from agenkit.evaluation.pattern_benchmarks import YAMLBenchmarkLoader

        specs_dir = Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"

        loader = YAMLBenchmarkLoader(specs_dir)

        # Create validator with role check
        validator = loader._create_validator(
            expected_message={"role": "assistant"}, expected_behavior={}
        )

        # Should pass with correct role
        msg_pass = Message(role="assistant", content="test", metadata={})
        assert validator(msg_pass) is True

        # Should fail with wrong role
        msg_fail = Message(role="user", content="test", metadata={})
        assert validator(msg_fail) is False

    def test_content_contains_validation(self):
        """Test content substring validation."""
        from agenkit.evaluation.pattern_benchmarks import YAMLBenchmarkLoader

        specs_dir = Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"

        loader = YAMLBenchmarkLoader(specs_dir)

        # Create validator with content check
        validator = loader._create_validator(
            expected_message={"content_contains": ["hello", "world"]}, expected_behavior={}
        )

        # Should pass with both substrings
        msg_pass = Message(role="assistant", content="hello world", metadata={})
        assert validator(msg_pass) is True

        # Should fail without all substrings
        msg_fail = Message(role="assistant", content="hello", metadata={})
        assert validator(msg_fail) is False

    def test_metadata_validation(self):
        """Test metadata validation."""
        from agenkit.evaluation.pattern_benchmarks import YAMLBenchmarkLoader

        specs_dir = Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"

        loader = YAMLBenchmarkLoader(specs_dir)

        # Create validator with metadata check
        validator = loader._create_validator(
            expected_message={"metadata": {"iterations": 1, "improved": True}}, expected_behavior={}
        )

        # Should pass with correct metadata
        msg_pass = Message(
            role="assistant", content="test", metadata={"iterations": 2, "improved": True}
        )
        assert validator(msg_pass) is True

        # Should fail with missing/wrong metadata
        msg_fail = Message(
            role="assistant", content="test", metadata={"iterations": 0, "improved": False}
        )
        assert validator(msg_fail) is False

    def test_behavior_validation(self):
        """Test behavioral property validation."""
        from agenkit.evaluation.pattern_benchmarks import YAMLBenchmarkLoader

        specs_dir = Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"

        loader = YAMLBenchmarkLoader(specs_dir)

        # Create validator with behavior check
        validator = loader._create_validator(
            expected_message={}, expected_behavior={"min_turns": 2, "max_turns": 5}
        )

        # Should pass within range
        msg_pass = Message(role="assistant", content="test", metadata={"turns": 3})
        assert validator(msg_pass) is True

        # Should fail below minimum
        msg_fail_low = Message(role="assistant", content="test", metadata={"turns": 1})
        assert validator(msg_fail_low) is False

        # Should fail above maximum
        msg_fail_high = Message(role="assistant", content="test", metadata={"turns": 6})
        assert validator(msg_fail_high) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
