"""
Pattern-specific benchmarks for evaluating agent patterns.

This module provides a comprehensive benchmark framework for evaluating all 18 core
agent patterns. It leverages the existing cross-language YAML test specifications
to automatically generate standardized test suites with validators, metrics, and
performance tracking.

Key Features:
    - Automatic conversion of YAML test specs to executable benchmarks
    - Pattern-specific test cases with validators
    - Performance measurement (latency, throughput)
    - Behavioral validation (turns, tool calls, metadata)
    - Support for all 18 core patterns

Classes:
    PatternBenchmark: Pattern-specific benchmark extending base Benchmark
    YAMLBenchmarkLoader: Loads benchmarks from YAML specification files
    PatternBenchmarkSuite: Collection of pattern benchmarks with execution support

Usage Example:
    >>> from pathlib import Path
    >>> from agenkit.evaluation.pattern_benchmarks import PatternBenchmarkSuite
    >>>
    >>> # Load all pattern benchmarks from YAML specs
    >>> specs_dir = Path("tests/cross_language/specs")
    >>> suite = PatternBenchmarkSuite.from_yaml_specs(specs_dir)
    >>>
    >>> # Get specific pattern benchmark
    >>> reflection = suite.get_benchmark("reflection")
    >>> print(f"Benchmark: {reflection.name}")
    >>> print(f"Test cases: {len(await reflection.generate_test_cases())}")
    >>>
    >>> # Run benchmark on agent
    >>> def agent_factory(config):
    >>>     return MyReflectionAgent(**config)
    >>>
    >>> results = await suite.run_benchmark(reflection, agent_factory)
    >>> print(f"Pass rate: {results['summary']['passed']}/{results['summary']['total']}")

Pattern Coverage:
    The framework supports benchmarks for all 18 core patterns:
    1. Reflection - Iterative self-improvement
    2. ReAct - Reasoning and acting with tools
    3. Sequential - Pipeline execution
    4. Parallel - Concurrent execution
    5. Router - Dynamic routing
    6. Planning - Task decomposition
    7. Conversational - Context-aware dialogue
    8. Task - Lifecycle management
    9. Multiagent - Agent collaboration
    10. Autonomous - Goal-driven behavior
    11. Memory Hierarchy - Multi-tier memory
    12. Agents-as-Tools - Agent delegation
    13. Fallback - Error recovery
    14. Collaborative - Consensus building
    15. Human-in-Loop - Approval workflows
    16. Supervisor - Task distribution
    17. Orchestration - Complex workflows
    18. Reasoning-with-Tools - Interleaved reasoning

Validators:
    Validators are automatically generated from YAML expected output specifications
    and can check:
    - Message role correctness
    - Content substring matching
    - Metadata presence and values
    - Behavioral properties (turn count, tool calls, etc.)

Performance Metrics:
    Each benchmark execution measures:
    - Individual test case latency (milliseconds)
    - Total execution time
    - Pass/fail rates
    - Output length
    - Custom metadata

See Also:
    - agenkit.evaluation.benchmarks: Base Benchmark and BenchmarkSuite classes
    - agenkit.evaluation.core: Core evaluation framework
    - tests/cross_language/specs/: YAML specification files
    - examples/evaluation/pattern_benchmarks_demo.py: Complete usage example
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Callable

import yaml

from agenkit.evaluation.benchmarks import Benchmark, BenchmarkSuite, TestCase
from agenkit.interfaces import Agent, Message


class PatternBenchmark(Benchmark):
    """
    Base class for pattern-specific benchmarks.

    Extends the base Benchmark class with pattern-specific validation
    and performance measurement capabilities.
    """

    def __init__(
        self,
        pattern_name: str,
        description: str,
        test_cases: list[TestCase],
    ):
        """
        Initialize pattern benchmark.

        Args:
            pattern_name: Name of the pattern (e.g., "reflection", "sequential")
            description: Human-readable description
            test_cases: Pre-generated test cases for this pattern
        """
        self._pattern_name = pattern_name
        self._description = description
        self._test_cases = test_cases

    @property
    def name(self) -> str:
        """Pattern benchmark name."""
        return f"{self._pattern_name}_benchmark"

    @property
    def description(self) -> str:
        """Pattern benchmark description."""
        return self._description

    async def generate_test_cases(self) -> list[TestCase]:
        """
        Generate test cases for this pattern.

        Returns:
            List of test cases loaded from YAML or generated
        """
        return self._test_cases


class YAMLBenchmarkLoader:
    """
    Load pattern benchmarks from YAML specifications.

    Converts YAML test scenarios into Benchmark objects compatible with
    the evaluation framework.
    """

    def __init__(self, specs_dir: Path | str):
        """
        Initialize YAML benchmark loader.

        Args:
            specs_dir: Directory containing YAML specification files
        """
        self.specs_dir = Path(specs_dir)
        if not self.specs_dir.exists():
            raise ValueError(f"Specs directory not found: {self.specs_dir}")

    def load_pattern_benchmark(self, pattern_name: str) -> PatternBenchmark:
        """
        Load benchmark for a specific pattern.

        Args:
            pattern_name: Pattern name (e.g., "reflection", "sequential")

        Returns:
            PatternBenchmark loaded from YAML specification

        Raises:
            FileNotFoundError: If YAML spec file not found
            ValueError: If YAML spec is invalid
        """
        # Find YAML file
        yaml_file = self.specs_dir / f"{pattern_name}.yaml"
        if not yaml_file.exists():
            raise FileNotFoundError(f"YAML spec not found: {yaml_file}")

        # Load YAML
        with open(yaml_file) as f:
            spec = yaml.safe_load(f)

        # Extract pattern info
        pattern_info = spec.get("pattern", {})
        pattern_display_name = pattern_info.get("name", pattern_name.title())
        pattern_description = pattern_info.get("description", f"Benchmark for {pattern_display_name} pattern")

        # Convert scenarios to test cases
        test_cases = []
        for scenario in spec.get("test_scenarios", []):
            test_case = self._scenario_to_test_case(scenario, pattern_name)
            test_cases.append(test_case)

        return PatternBenchmark(
            pattern_name=pattern_name,
            description=pattern_description,
            test_cases=test_cases,
        )

    def load_all_pattern_benchmarks(self) -> list[PatternBenchmark]:
        """
        Load benchmarks for all patterns in specs directory.

        Returns:
            List of all pattern benchmarks
        """
        benchmarks = []

        # Find all YAML files
        for yaml_file in self.specs_dir.glob("*.yaml"):
            pattern_name = yaml_file.stem
            try:
                benchmark = self.load_pattern_benchmark(pattern_name)
                benchmarks.append(benchmark)
            except Exception as e:
                print(f"Warning: Failed to load benchmark for {pattern_name}: {e}")

        return benchmarks

    def _scenario_to_test_case(self, scenario: dict, pattern_name: str) -> TestCase:
        """
        Convert YAML test scenario to TestCase.

        Args:
            scenario: Scenario dictionary from YAML
            pattern_name: Name of the pattern

        Returns:
            TestCase object
        """
        scenario_id = scenario.get("id", "unknown")
        scenario_name = scenario.get("name", scenario_id)

        # Extract input
        input_data = scenario.get("input", {})
        input_message = input_data.get("message", {})
        input_content = input_message.get("content", "")

        # Extract expected output
        expected_output = scenario.get("expected_output", {})
        expected_message = expected_output.get("message", {})

        # Create validation function from expected output
        expected = self._create_validator(expected_message, expected_output.get("behavior", {}))

        # Build metadata
        metadata = {
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "pattern": pattern_name,
            "config": input_data.get("config", {}),
        }

        # Extract behavior expectations
        behavior = expected_output.get("behavior", {})
        if behavior:
            metadata["expected_behavior"] = behavior

        # Extract tags
        tags = [pattern_name, "yaml_generated"]
        if "description" in scenario:
            # Extract complexity tags
            description = scenario["description"].lower()
            if "basic" in description or "simple" in description:
                tags.append("basic")
            elif "complex" in description or "advanced" in description:
                tags.append("complex")

        return TestCase(
            input=input_content,
            expected=expected,
            metadata=metadata,
            tags=tags,
        )

    def _create_validator(
        self,
        expected_message: dict,
        expected_behavior: dict
    ) -> Callable[[Message], bool]:
        """
        Create validation function from expected output specification.

        Args:
            expected_message: Expected message properties
            expected_behavior: Expected behavioral properties

        Returns:
            Validation function that checks if a Message meets expectations
        """
        def validator(msg: Message) -> bool:
            """Validate message against expected output."""
            # Check role
            if "role" in expected_message:
                expected_role = expected_message["role"]
                if msg.role != expected_role:
                    return False

            # Check content contains
            if "content_contains" in expected_message:
                content = str(msg.content).lower()
                for substring in expected_message["content_contains"]:
                    if substring.lower() not in content:
                        return False

            # Check metadata
            if "metadata" in expected_message:
                for key, expected_value in expected_message["metadata"].items():
                    actual_value = msg.metadata.get(key)
                    # For numeric values, check minimum
                    if isinstance(expected_value, (int, float)):
                        if actual_value is None or actual_value < expected_value:
                            return False
                    # For boolean values, check exact match
                    elif isinstance(expected_value, bool):
                        if actual_value != expected_value:
                            return False

            # Check behavioral properties (stored in metadata by harnesses)
            if expected_behavior:
                # Min turns
                if "min_turns" in expected_behavior:
                    turns = msg.metadata.get("turns", 0)
                    if turns < expected_behavior["min_turns"]:
                        return False

                # Max turns
                if "max_turns" in expected_behavior:
                    turns = msg.metadata.get("turns", 0)
                    if turns > expected_behavior["max_turns"]:
                        return False

                # Tool calls
                if "tool_calls" in expected_behavior:
                    expected_tools = expected_behavior["tool_calls"]
                    actual_tools = msg.metadata.get("tool_calls", [])
                    for expected_tool in expected_tools:
                        if expected_tool not in actual_tools:
                            return False

            return True

        return validator


class PatternBenchmarkSuite:
    """
    Suite of pattern benchmarks for comprehensive evaluation.

    Provides convenience methods for running benchmarks on all patterns
    or specific subsets.
    """

    def __init__(self, benchmarks: list[PatternBenchmark] | None = None):
        """
        Initialize pattern benchmark suite.

        Args:
            benchmarks: List of pattern benchmarks
        """
        self.benchmarks = benchmarks or []

    @classmethod
    def from_yaml_specs(cls, specs_dir: Path | str) -> "PatternBenchmarkSuite":
        """
        Create suite from YAML specifications directory.

        Args:
            specs_dir: Directory containing YAML spec files

        Returns:
            PatternBenchmarkSuite with all patterns loaded
        """
        loader = YAMLBenchmarkLoader(specs_dir)
        benchmarks = loader.load_all_pattern_benchmarks()
        return cls(benchmarks=benchmarks)

    @classmethod
    def standard_patterns(cls) -> "PatternBenchmarkSuite":
        """
        Create suite with standard pattern benchmarks.

        Includes the most commonly used patterns.

        Returns:
            Suite with sequential, parallel, router, reflection, react
        """
        # This will be populated by loading from default specs location
        specs_dir = Path(__file__).parent.parent.parent / "tests" / "cross_language" / "specs"
        if specs_dir.exists():
            return cls.from_yaml_specs(specs_dir)
        return cls(benchmarks=[])

    def get_benchmark(self, pattern_name: str) -> PatternBenchmark | None:
        """
        Get benchmark for specific pattern.

        Args:
            pattern_name: Name of the pattern

        Returns:
            PatternBenchmark if found, None otherwise
        """
        for benchmark in self.benchmarks:
            if benchmark._pattern_name == pattern_name:
                return benchmark
        return None

    def get_benchmarks_by_tag(self, tag: str) -> list[PatternBenchmark]:
        """
        Get benchmarks that have test cases with specific tag.

        Args:
            tag: Tag to filter by (e.g., "basic", "complex")

        Returns:
            List of benchmarks containing the tag
        """
        matching = []
        for benchmark in self.benchmarks:
            for test_case in benchmark._test_cases:
                if tag in test_case.tags:
                    matching.append(benchmark)
                    break
        return matching

    async def run_benchmark(
        self,
        benchmark: PatternBenchmark,
        agent_factory: Callable[[dict], Agent],
    ) -> dict[str, Any]:
        """
        Run a benchmark and collect results.

        Args:
            benchmark: Benchmark to run
            agent_factory: Function that creates agent from config

        Returns:
            Dictionary with benchmark results
        """
        results = {
            "pattern": benchmark._pattern_name,
            "test_cases": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "total_time_ms": 0,
            }
        }

        test_cases = await benchmark.generate_test_cases()

        for test_case in test_cases:
            # Create agent with config from test case
            config = test_case.metadata.get("config", {})
            agent = agent_factory(config)

            # Run test case
            start_time = time.perf_counter()

            try:
                # Create input message
                input_msg = Message(
                    role="user",
                    content=test_case.input,
                    metadata={}
                )

                # Process with agent
                output_msg = await agent.process(input_msg)

                # Measure time
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                # Validate output
                if callable(test_case.expected):
                    passed = test_case.expected(output_msg)
                else:
                    passed = str(output_msg.content) == str(test_case.expected)

                results["test_cases"].append({
                    "scenario_id": test_case.metadata.get("scenario_id", "unknown"),
                    "passed": passed,
                    "time_ms": elapsed_ms,
                    "output_length": len(str(output_msg.content)),
                })

                if passed:
                    results["summary"]["passed"] += 1
                else:
                    results["summary"]["failed"] += 1

                results["summary"]["total_time_ms"] += elapsed_ms

            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                results["test_cases"].append({
                    "scenario_id": test_case.metadata.get("scenario_id", "unknown"),
                    "passed": False,
                    "error": str(e),
                    "time_ms": elapsed_ms,
                })

                results["summary"]["failed"] += 1
                results["summary"]["total_time_ms"] += elapsed_ms

            results["summary"]["total"] += 1

        return results

    async def run_all_benchmarks(
        self,
        agent_factory: Callable[[str, dict], Agent],
    ) -> dict[str, Any]:
        """
        Run all benchmarks in the suite.

        Args:
            agent_factory: Function that creates agent from (pattern_name, config)

        Returns:
            Dictionary with all benchmark results
        """
        all_results = {
            "benchmarks": [],
            "summary": {
                "total_patterns": len(self.benchmarks),
                "total_test_cases": 0,
                "total_passed": 0,
                "total_failed": 0,
                "total_time_ms": 0,
            }
        }

        for benchmark in self.benchmarks:
            # Create pattern-specific agent factory
            pattern_agent_factory = lambda config: agent_factory(benchmark._pattern_name, config)

            # Run benchmark
            results = await self.run_benchmark(benchmark, pattern_agent_factory)
            all_results["benchmarks"].append(results)

            # Update summary
            all_results["summary"]["total_test_cases"] += results["summary"]["total"]
            all_results["summary"]["total_passed"] += results["summary"]["passed"]
            all_results["summary"]["total_failed"] += results["summary"]["failed"]
            all_results["summary"]["total_time_ms"] += results["summary"]["total_time_ms"]

        return all_results

    def to_dict(self) -> dict:
        """Convert suite to dictionary."""
        return {
            "patterns": [b._pattern_name for b in self.benchmarks],
            "total_benchmarks": len(self.benchmarks),
            "descriptions": {
                b._pattern_name: b._description
                for b in self.benchmarks
            }
        }
