"""
Cross-language test specification loader.

Loads and validates YAML pattern specifications.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class Message:
    """Test message structure."""

    role: str
    content: str
    metadata: Dict[str, Any]


@dataclass
class ExpectedBehavior:
    """Expected behavioral characteristics."""

    min_turns: Optional[int] = None
    max_turns: Optional[int] = None
    tool_calls: Optional[List[str]] = None
    sub_agents: Optional[List[str]] = None
    custom: Optional[Dict[str, Any]] = None


@dataclass
class ExpectedOutput:
    """Expected test output."""

    message: Optional[Dict[str, Any]] = None
    behavior: Optional[ExpectedBehavior] = None
    metadata: Optional[Dict[str, Any]] = None
    error: bool = False


@dataclass
class TestScenario:
    """Single test scenario."""

    id: str
    name: str
    description: str
    input: Dict[str, Any]
    expected_output: ExpectedOutput


@dataclass
class PatternProperties:
    """Pattern behavioral properties."""

    deterministic: bool
    idempotent: bool
    stateful: bool
    requires_llm: bool
    supports_streaming: bool


@dataclass
class PatternSpec:
    """Complete pattern specification."""

    name: str
    description: str
    category: str
    test_scenarios: List[TestScenario]
    edge_cases: List[Dict[str, str]]
    properties: PatternProperties
    performance: Dict[str, str]
    dependencies: Dict[str, List[str]]


class SpecificationLoader:
    """Loads and validates pattern specifications."""

    def __init__(self, specs_dir: Path):
        """
        Initialize specification loader.

        Args:
            specs_dir: Directory containing YAML specifications
        """
        self.specs_dir = Path(specs_dir)
        if not self.specs_dir.exists():
            raise FileNotFoundError(f"Specs directory not found: {specs_dir}")

    def load_spec(self, pattern_name: str) -> PatternSpec:
        """
        Load specification for a pattern.

        Args:
            pattern_name: Name of pattern to load

        Returns:
            Loaded and validated pattern specification

        Raises:
            FileNotFoundError: Specification file not found
            ValueError: Invalid specification format
        """
        spec_path = self.specs_dir / f"{pattern_name}.yaml"
        if not spec_path.exists():
            raise FileNotFoundError(f"Specification not found: {spec_path}")

        with open(spec_path) as f:
            data = yaml.safe_load(f)

        return self._parse_spec(data)

    def load_all_specs(self) -> Dict[str, PatternSpec]:
        """
        Load all pattern specifications.

        Returns:
            Dictionary mapping pattern names to specifications
        """
        specs = {}
        for spec_file in self.specs_dir.glob("*.yaml"):
            if spec_file.stem in ("SCHEMA", "README"):
                continue
            try:
                spec = self.load_spec(spec_file.stem)
                specs[spec.name] = spec
            except Exception as e:
                print(f"Warning: Failed to load {spec_file}: {e}")
        return specs

    def _parse_spec(self, data: Dict[str, Any]) -> PatternSpec:
        """Parse specification data into PatternSpec object."""
        pattern_data = data.get("pattern", {})
        scenarios_data = data.get("test_scenarios", [])
        edge_cases = data.get("edge_cases", [])
        properties_data = data.get("properties", {})
        performance_data = data.get("performance", {})
        dependencies_data = data.get("dependencies", {})

        # Parse test scenarios
        scenarios = []
        for scenario_data in scenarios_data:
            scenario = self._parse_scenario(scenario_data)
            scenarios.append(scenario)

        # Parse properties
        properties = PatternProperties(
            deterministic=properties_data.get("deterministic", False),
            idempotent=properties_data.get("idempotent", False),
            stateful=properties_data.get("stateful", False),
            requires_llm=properties_data.get("requires_llm", False),
            supports_streaming=properties_data.get("supports_streaming", False),
        )

        return PatternSpec(
            name=pattern_data.get("name", ""),
            description=pattern_data.get("description", ""),
            category=pattern_data.get("category", ""),
            test_scenarios=scenarios,
            edge_cases=edge_cases,
            properties=properties,
            performance=performance_data,
            dependencies=dependencies_data,
        )

    def _parse_scenario(self, data: Dict[str, Any]) -> TestScenario:
        """Parse scenario data into TestScenario object."""
        expected_data = data.get("expected_output", {})

        # Parse expected behavior
        behavior_data = expected_data.get("behavior", {})
        behavior = None
        if behavior_data:
            behavior = ExpectedBehavior(
                min_turns=behavior_data.get("min_turns"),
                max_turns=behavior_data.get("max_turns"),
                tool_calls=behavior_data.get("tool_calls"),
                sub_agents=behavior_data.get("sub_agents"),
                custom={
                    k: v
                    for k, v in behavior_data.items()
                    if k not in ("min_turns", "max_turns", "tool_calls", "sub_agents")
                },
            )

        expected_output = ExpectedOutput(
            message=expected_data.get("message"),
            behavior=behavior,
            metadata=expected_data.get("metadata"),
            error=expected_data.get("error", False),
        )

        return TestScenario(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            input=data.get("input", {}),
            expected_output=expected_output,
        )

    def validate_spec(self, spec: PatternSpec) -> List[str]:
        """
        Validate a pattern specification.

        Args:
            spec: Pattern specification to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Validate pattern metadata
        if not spec.name:
            errors.append("Pattern name is required")
        if not spec.description:
            errors.append("Pattern description is required")
        if not spec.category:
            errors.append("Pattern category is required")

        # Validate test scenarios
        if not spec.test_scenarios:
            errors.append("At least one test scenario is required")

        scenario_ids = set()
        for scenario in spec.test_scenarios:
            # Check for duplicate IDs
            if scenario.id in scenario_ids:
                errors.append(f"Duplicate scenario ID: {scenario.id}")
            scenario_ids.add(scenario.id)

            # Validate scenario fields
            if not scenario.id:
                errors.append("Scenario ID is required")
            if not scenario.name:
                errors.append(f"Scenario name is required for {scenario.id}")
            if not scenario.input:
                errors.append(f"Scenario input is required for {scenario.id}")

            # Validate regex patterns
            if scenario.expected_output.message:
                pattern = scenario.expected_output.message.get("content_pattern")
                if pattern:
                    try:
                        re.compile(pattern)
                    except re.error as e:
                        errors.append(
                            f"Invalid regex pattern in {scenario.id}: {pattern} - {e}"
                        )

        return errors

    def get_patterns_by_category(
        self, specs: Dict[str, PatternSpec]
    ) -> Dict[str, List[str]]:
        """
        Group patterns by category.

        Args:
            specs: Dictionary of pattern specifications

        Returns:
            Dictionary mapping categories to pattern names
        """
        categories: Dict[str, List[str]] = {}
        for name, spec in specs.items():
            category = spec.category
            if category not in categories:
                categories[category] = []
            categories[category].append(name)
        return categories

    def get_patterns_requiring_llm(self, specs: Dict[str, PatternSpec]) -> List[str]:
        """
        Get patterns that require LLM access.

        Args:
            specs: Dictionary of pattern specifications

        Returns:
            List of pattern names requiring LLM
        """
        return [name for name, spec in specs.items() if spec.properties.requires_llm]
