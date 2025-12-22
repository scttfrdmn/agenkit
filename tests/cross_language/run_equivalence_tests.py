#!/usr/bin/env python3
"""
Cross-language equivalence test runner.

Executes pattern specifications across all 6 languages and validates
behavioral equivalence.
"""

import argparse
import json
import sys
from pathlib import Path

from harness_manager import (HarnessConfig, HarnessManager, TestRequest,
                             discover_harnesses)
from result_comparator import ResultComparator
from spec_loader import PatternSpec, SpecificationLoader


class EquivalenceTestRunner:
    """Runs cross-language equivalence tests."""

    def __init__(
        self,
        specs_dir: Path,
        harness_configs: list[HarnessConfig],
        languages: list[str] | None = None,
    ):
        """
        Initialize test runner.

        Args:
            specs_dir: Directory containing YAML specifications
            harness_configs: List of harness configurations
            languages: Optional list of languages to test (default: all)
        """
        self.spec_loader = SpecificationLoader(specs_dir)
        self.harness_manager = HarnessManager(harness_configs)
        self.comparator = ResultComparator()
        self.languages = languages or self.harness_manager.get_available_languages()

    def run_all_tests(self, patterns: list[str] | None = None) -> dict[str, dict[str, any]]:
        """
        Run all equivalence tests.

        Args:
            patterns: Optional list of patterns to test (default: all)

        Returns:
            Dictionary of test results
        """
        # Load specifications
        all_specs = self.spec_loader.load_all_specs()

        if patterns:
            # Filter to requested patterns (case-insensitive)
            patterns_lower = [p.lower() for p in patterns]
            all_specs = {
                name: spec for name, spec in all_specs.items() if name.lower() in patterns_lower
            }

        print(f"Running equivalence tests for {len(all_specs)} patterns...")
        print(f"Languages: {', '.join(self.languages)}")
        print()

        results = {}

        for pattern_name, spec in all_specs.items():
            print(f"Testing pattern: {pattern_name}")
            pattern_results = self._test_pattern(spec)
            results[pattern_name] = pattern_results
            print()

        return results

    def _test_pattern(self, spec: PatternSpec) -> dict[str, any]:
        """Test a single pattern across all languages."""
        pattern_results = {
            "pattern": spec.name,
            "scenarios": {},
            "summary": {},
        }

        for scenario in spec.test_scenarios:
            print(f"  Scenario: {scenario.name}")
            scenario_results = self._test_scenario(spec, scenario)
            pattern_results["scenarios"][scenario.id] = scenario_results

        # Summarize pattern results
        total_scenarios = len(spec.test_scenarios)

        def scenario_passed(scenario_result):
            """Check if scenario passed - either by equivalence or validation."""
            equivalence = scenario_result.get("equivalence", {})
            # For multi-language: check if all comparisons are equivalent
            if equivalence.get("total_comparisons", 0) > 0:
                return equivalence.get("equivalence_rate", 0.0) == 1.0
            # For single-language: check if validation passed
            language_results = scenario_result.get("language_results", {})
            return all(
                lr.get("validation", {}).get("valid", False) for lr in language_results.values()
            )

        passed_scenarios = sum(
            1 for s in pattern_results["scenarios"].values() if scenario_passed(s)
        )

        pattern_results["summary"] = {
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_scenarios,
            "failed_scenarios": total_scenarios - passed_scenarios,
            "pass_rate": passed_scenarios / total_scenarios if total_scenarios > 0 else 0.0,
        }

        print(f"  Pattern summary: {passed_scenarios}/{total_scenarios} scenarios passed")

        return pattern_results

    def _test_scenario(self, spec: PatternSpec, scenario) -> dict[str, any]:
        """Test a single scenario across all languages."""
        # Build test request
        request = TestRequest(
            pattern=spec.name,
            scenario_id=scenario.id,
            input_data=scenario.input,
        )

        # Execute on all languages
        language_results = {}
        for language in self.languages:
            print(f"    {language}...", end=" ", flush=True)
            try:
                result = self.harness_manager.execute_test(language, request)
                language_results[language] = {
                    "status": result.status,
                    "output": result.output,
                    "error": result.error,
                    "execution_info": result.execution_info,
                }

                # Validate against expected output
                validation = self.comparator.validate_output(
                    language_results[language], scenario.expected_output
                )

                language_results[language]["validation"] = {
                    "valid": validation.valid,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                }

                if validation.valid:
                    print("✓")
                else:
                    print(f"✗ ({len(validation.errors)} errors)")
                    for error in validation.errors[:3]:  # Show first 3 errors
                        print(f"      - {error}")

            except Exception as e:
                print(f"ERROR: {e}")
                language_results[language] = {
                    "status": "error",
                    "error": {
                        "type": type(e).__name__,
                        "message": str(e),
                    },
                    "validation": {
                        "valid": False,
                        "errors": [str(e)],
                        "warnings": [],
                    },
                }

        # Compare results across languages
        comparisons = self.comparator.compare_all_languages(language_results)
        equivalence_summary = self.comparator.summarize_equivalence(comparisons)

        return {
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "language_results": language_results,
            "comparisons": {
                k: {
                    "equivalent": v.equivalent,
                    "differences": v.differences,
                    "warnings": v.warnings,
                }
                for k, v in comparisons.items()
            },
            "equivalence": equivalence_summary,
        }

    def generate_report(self, results: dict[str, dict[str, any]], output_path: Path):
        """
        Generate test report.

        Args:
            results: Test results
            output_path: Path to save report
        """
        # Generate summary
        total_patterns = len(results)
        total_scenarios = sum(len(r["scenarios"]) for r in results.values())
        passed_patterns = sum(1 for r in results.values() if r["summary"]["pass_rate"] == 1.0)

        report = {
            "summary": {
                "total_patterns": total_patterns,
                "passed_patterns": passed_patterns,
                "total_scenarios": total_scenarios,
                "languages_tested": self.languages,
            },
            "patterns": results,
        }

        # Save as JSON
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {output_path}")

        # Print summary
        print("\n" + "=" * 80)
        print("EQUIVALENCE TEST SUMMARY")
        print("=" * 80)
        print(f"Total patterns tested: {total_patterns}")
        print(f"Patterns with 100% equivalence: {passed_patterns}/{total_patterns}")
        print(f"Total scenarios tested: {total_scenarios}")
        print(f"Languages tested: {', '.join(self.languages)}")
        print("=" * 80)

        # Print pattern details
        for pattern_name, pattern_results in results.items():
            summary = pattern_results["summary"]
            status_icon = "✓" if summary["pass_rate"] == 1.0 else "✗"
            print(
                f"{status_icon} {pattern_name}: {summary['passed_scenarios']}/{summary['total_scenarios']} scenarios"
            )

        print("=" * 80)

    def health_check_harnesses(self) -> bool:
        """
        Check health of all harnesses before running tests.

        Returns:
            True if all harnesses are healthy
        """
        print("Checking harness health...")
        health_status = self.harness_manager.health_check_all()

        all_healthy = True
        for language, healthy in health_status.items():
            status = "✓" if healthy else "✗"
            print(f"  {status} {language}")
            if not healthy:
                all_healthy = False

        if not all_healthy:
            print("\nWARNING: Some harnesses are unhealthy!")

        return all_healthy


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run cross-language equivalence tests")
    parser.add_argument(
        "--patterns",
        nargs="+",
        help="Specific patterns to test (default: all)",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        choices=["python", "go", "typescript", "rust", "cpp", "zig"],
        help="Languages to test (default: all available)",
    )
    parser.add_argument(
        "--specs-dir",
        type=Path,
        default=Path(__file__).parent / "specs",
        help="Directory containing pattern specifications",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("equivalence_report.json"),
        help="Path to save test report",
    )
    parser.add_argument(
        "--health-check-only",
        action="store_true",
        help="Only check harness health, don't run tests",
    )

    args = parser.parse_args()

    # Discover harnesses
    root_dir = Path(__file__).parent.parent.parent
    harness_configs = discover_harnesses(root_dir)

    if not harness_configs:
        print("ERROR: No harnesses found!", file=sys.stderr)
        print("Please build the harnesses first.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(harness_configs)} harnesses")

    # Filter to requested languages
    if args.languages:
        harness_configs = [h for h in harness_configs if h.language in args.languages]

    # Create runner
    runner = EquivalenceTestRunner(
        specs_dir=args.specs_dir,
        harness_configs=harness_configs,
        languages=args.languages,
    )

    # Health check
    if not runner.health_check_harnesses():
        if args.health_check_only:
            sys.exit(1)
        print("\nContinuing with available harnesses...")

    if args.health_check_only:
        sys.exit(0)

    # Run tests
    results = runner.run_all_tests(patterns=args.patterns)

    # Generate report
    runner.generate_report(results, args.report)

    # Exit with non-zero if any tests failed
    all_passed = all(r["summary"]["pass_rate"] == 1.0 for r in results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
