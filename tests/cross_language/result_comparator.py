"""
Cross-language result comparison and validation.

Compares test results across languages and validates behavioral equivalence.
"""

import re
from dataclasses import dataclass
from typing import Any

from spec_loader import ExpectedOutput


@dataclass
class ComparisonResult:
    """Result of comparing outputs from two languages."""

    equivalent: bool
    differences: list[str]
    warnings: list[str]


@dataclass
class ValidationResult:
    """Result of validating output against expected behavior."""

    valid: bool
    errors: list[str]
    warnings: list[str]


class ResultComparator:
    """Compares and validates test results."""

    def __init__(self, tolerance_config: dict[str, Any] | None = None):
        """
        Initialize result comparator.

        Args:
            tolerance_config: Tolerance configuration for comparisons
        """
        self.tolerance = tolerance_config or self._default_tolerance()

    @staticmethod
    def _default_tolerance() -> dict[str, Any]:
        """Get default tolerance configuration."""
        return {
            "float_epsilon": 1e-6,  # Floating point comparison tolerance
            "timestamp_ignore": True,  # Ignore timestamp differences
            "llm_content_exact": False,  # Don't require exact LLM output match
            "metadata_strict": False,  # Allow extra metadata fields
        }

    def validate_output(self, output: dict[str, Any], expected: ExpectedOutput) -> ValidationResult:
        """
        Validate output against expected behavior.

        Args:
            output: Actual output from test
            expected: Expected output specification

        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []

        # Validate message content
        if expected.message:
            message_errors = self._validate_message(
                output.get("output", {}).get("message", {}),
                expected.message,
            )
            errors.extend(message_errors)

        # Validate behavior
        if expected.behavior:
            behavior_errors = self._validate_behavior(
                output.get("output", {}).get("behavior", {}),
                expected.behavior,
            )
            errors.extend(behavior_errors)

        # Check for error expectation
        if expected.error:
            if output.get("status") != "error":
                errors.append("Expected error but got success")
            # For error scenarios, validate metadata from error details
            elif expected.metadata:
                error_metadata = output.get("error", {}).get("details", {})
                metadata_errors = self._validate_metadata(
                    error_metadata,
                    expected.metadata,
                )
                errors.extend(metadata_errors)
        # For success scenarios, validate metadata from message
        elif expected.metadata:
            metadata_errors = self._validate_metadata(
                output.get("output", {}).get("message", {}).get("metadata", {}),
                expected.metadata,
            )
            errors.extend(metadata_errors)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_message(self, actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
        """Validate message content."""
        errors = []

        # Check role
        expected_role = expected.get("role")
        if expected_role:
            actual_role = actual.get("role")
            if actual_role != expected_role:
                errors.append(f"Role mismatch: expected '{expected_role}', got '{actual_role}'")

        # Check content_contains
        content_contains = expected.get("content_contains", [])
        actual_content = actual.get("content", "")
        for substring in content_contains:
            if substring not in actual_content:
                errors.append(f"Content missing required substring: '{substring}'")

        # Check content_not_contains
        content_not_contains = expected.get("content_not_contains", [])
        for substring in content_not_contains:
            if substring in actual_content:
                errors.append(f"Content contains forbidden substring: '{substring}'")

        # Check content_pattern
        content_pattern = expected.get("content_pattern")
        if content_pattern:
            try:
                if not re.search(content_pattern, actual_content):
                    errors.append(f"Content does not match pattern: {content_pattern}")
            except re.error as e:
                errors.append(f"Invalid regex pattern: {content_pattern} - {e}")

        return errors

    def _validate_behavior(self, actual: dict[str, Any], expected) -> list[str]:
        """Validate behavioral characteristics."""
        errors = []

        # Check min_turns
        if expected.min_turns is not None:
            actual_turns = actual.get("turns", 0)
            if actual_turns < expected.min_turns:
                errors.append(
                    f"Too few turns: expected >= {expected.min_turns}, got {actual_turns}"
                )

        # Check max_turns
        if expected.max_turns is not None:
            actual_turns = actual.get("turns", 0)
            if actual_turns > expected.max_turns:
                errors.append(
                    f"Too many turns: expected <= {expected.max_turns}, got {actual_turns}"
                )

        # Check tool_calls
        if expected.tool_calls is not None:
            actual_tools = actual.get("tool_calls", [])
            for expected_tool in expected.tool_calls:
                if expected_tool not in actual_tools:
                    errors.append(f"Expected tool call not found: '{expected_tool}'")

        # Check sub_agents
        if expected.sub_agents is not None:
            actual_agents = actual.get("sub_agents", [])
            for expected_agent in expected.sub_agents:
                if expected_agent not in actual_agents:
                    errors.append(f"Expected sub-agent not found: '{expected_agent}'")

        return errors

    def _validate_metadata(self, actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
        """Validate metadata fields."""
        errors = []

        for key, expected_value in expected.items():
            if key not in actual:
                if not self.tolerance.get("metadata_strict"):
                    # Allow missing optional metadata
                    continue
                errors.append(f"Missing expected metadata field: '{key}'")
                continue

            actual_value = actual[key]

            # Handle nested dict comparison for ranges
            if isinstance(expected_value, dict) and "min" in expected_value:
                # Range comparison
                min_val = expected_value.get("min")
                max_val = expected_value.get("max")
                if min_val is not None and actual_value < min_val:
                    errors.append(
                        f"Metadata '{key}' below minimum: expected >= {min_val}, got {actual_value}"
                    )
                if max_val is not None and actual_value > max_val:
                    errors.append(
                        f"Metadata '{key}' above maximum: expected <= {max_val}, got {actual_value}"
                    )
            elif actual_value != expected_value:
                errors.append(
                    f"Metadata mismatch for '{key}': expected {expected_value}, got {actual_value}"
                )

        return errors

    def compare_outputs(
        self, output1: dict[str, Any], output2: dict[str, Any], language1: str, language2: str
    ) -> ComparisonResult:
        """
        Compare outputs from two different language implementations.

        Args:
            output1: Output from first language
            output2: Output from second language
            language1: Name of first language
            language2: Name of second language

        Returns:
            Comparison result indicating equivalence
        """
        differences = []
        warnings = []

        # Compare statuses
        status1 = output1.get("status")
        status2 = output2.get("status")
        if status1 != status2:
            differences.append(f"Status mismatch: {language1}={status1}, {language2}={status2}")

        # If both errored, compare error types
        if status1 == "error" and status2 == "error":
            error1_type = output1.get("error", {}).get("type", "")
            error2_type = output2.get("error", {}).get("type", "")
            if error1_type != error2_type:
                differences.append(
                    f"Error type mismatch: {language1}={error1_type}, {language2}={error2_type}"
                )
            # Error messages can differ slightly - just warn
            error1_msg = output1.get("error", {}).get("message", "")
            error2_msg = output2.get("error", {}).get("message", "")
            if error1_msg != error2_msg:
                warnings.append(f"Error message differs (acceptable): {language1} vs {language2}")

        # Compare successful outputs
        if status1 == "success" and status2 == "success":
            result1 = output1.get("output", {})
            result2 = output2.get("output", {})

            # Compare message roles
            role1 = result1.get("message", {}).get("role")
            role2 = result2.get("message", {}).get("role")
            if role1 != role2:
                differences.append(f"Role mismatch: {language1}={role1}, {language2}={role2}")

            # Compare message content (fuzzy for LLM outputs)
            if not self.tolerance.get("llm_content_exact"):
                # For LLM outputs, just check both are non-empty
                content1 = result1.get("message", {}).get("content", "")
                content2 = result2.get("message", {}).get("content", "")
                if bool(content1) != bool(content2):
                    differences.append(
                        f"Content presence mismatch: {language1}={'present' if content1 else 'empty'}, {language2}={'present' if content2 else 'empty'}"
                    )
            else:
                # Exact content comparison
                content1 = result1.get("message", {}).get("content", "")
                content2 = result2.get("message", {}).get("content", "")
                if content1 != content2:
                    differences.append(f"Content mismatch between {language1} and {language2}")

            # Compare metadata (ignoring timestamps if configured)
            metadata_diff = self._compare_metadata(
                result1.get("message", {}).get("metadata", {}),
                result2.get("message", {}).get("metadata", {}),
                language1,
                language2,
            )
            differences.extend(metadata_diff)

            # Compare behavior
            behavior_diff = self._compare_behavior(
                result1.get("behavior", {}),
                result2.get("behavior", {}),
                language1,
                language2,
            )
            differences.extend(behavior_diff)

        return ComparisonResult(
            equivalent=len(differences) == 0,
            differences=differences,
            warnings=warnings,
        )

    def _compare_metadata(
        self, meta1: dict[str, Any], meta2: dict[str, Any], lang1: str, lang2: str
    ) -> list[str]:
        """Compare metadata dictionaries."""
        differences = []

        # Get all keys
        all_keys = set(meta1.keys()) | set(meta2.keys())

        # Ignore timestamp fields if configured
        if self.tolerance.get("timestamp_ignore"):
            all_keys -= {"timestamp", "created_at", "updated_at"}

        for key in all_keys:
            val1 = meta1.get(key)
            val2 = meta2.get(key)

            if val1 != val2:
                # Check if both are numbers (allow floating point tolerance)
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    if abs(val1 - val2) > self.tolerance.get("float_epsilon", 1e-6):
                        differences.append(
                            f"Metadata '{key}' mismatch: {lang1}={val1}, {lang2}={val2}"
                        )
                else:
                    differences.append(f"Metadata '{key}' mismatch: {lang1}={val1}, {lang2}={val2}")

        return differences

    def _compare_behavior(
        self, behavior1: dict[str, Any], behavior2: dict[str, Any], lang1: str, lang2: str
    ) -> list[str]:
        """Compare behavioral characteristics."""
        differences = []

        # Compare numeric fields
        for key in ["turns", "iterations"]:
            val1 = behavior1.get(key)
            val2 = behavior2.get(key)
            if val1 is not None and val2 is not None and val1 != val2:
                differences.append(f"Behavior '{key}' mismatch: {lang1}={val1}, {lang2}={val2}")

        # Compare list fields
        for key in ["tool_calls", "sub_agents"]:
            list1 = behavior1.get(key, [])
            list2 = behavior2.get(key, [])
            # Use sorted comparison for lists that might contain dicts
            try:
                if set(list1) != set(list2):
                    differences.append(
                        f"Behavior '{key}' mismatch: {lang1}={list1}, {lang2}={list2}"
                    )
            except TypeError:
                # Lists contain unhashable items (like dicts), use direct comparison
                if sorted(list1, key=str) != sorted(list2, key=str):
                    differences.append(
                        f"Behavior '{key}' mismatch: {lang1}={list1}, {lang2}={list2}"
                    )

        return differences

    def compare_all_languages(
        self, results: dict[str, dict[str, Any]]
    ) -> dict[str, list[ComparisonResult]]:
        """
        Compare results across all language pairs.

        Args:
            results: Dictionary mapping language names to test results

        Returns:
            Dictionary mapping language pairs to comparison results
        """
        comparisons = {}
        languages = sorted(results.keys())

        for i, lang1 in enumerate(languages):
            for lang2 in languages[i + 1 :]:
                pair_key = f"{lang1}_vs_{lang2}"
                comparison = self.compare_outputs(results[lang1], results[lang2], lang1, lang2)
                comparisons[pair_key] = comparison

        return comparisons

    def summarize_equivalence(self, comparisons: dict[str, ComparisonResult]) -> dict[str, Any]:
        """
        Summarize equivalence across all comparisons.

        Args:
            comparisons: Dictionary of comparison results

        Returns:
            Summary statistics
        """
        total = len(comparisons)
        equivalent = sum(1 for c in comparisons.values() if c.equivalent)

        all_differences = []
        all_warnings = []
        for comp in comparisons.values():
            all_differences.extend(comp.differences)
            all_warnings.extend(comp.warnings)

        return {
            "total_comparisons": total,
            "equivalent_count": equivalent,
            "different_count": total - equivalent,
            "equivalence_rate": equivalent / total if total > 0 else 0.0,
            "all_differences": all_differences,
            "all_warnings": all_warnings,
        }
