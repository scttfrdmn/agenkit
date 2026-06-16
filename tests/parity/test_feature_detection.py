"""Tests for feature detection scanners.

Validates that scanners accurately detect features without false
positives or false negatives.
"""

import json
from pathlib import Path

import pytest

# Import scanners
from scripts.parity.scanners import go_scanner, python_scanner, typescript_scanner


@pytest.fixture
def feature_manifest():
    """Load generated feature manifest if it exists."""
    manifest_path = Path("feature-manifest.json")
    if manifest_path.exists():
        with manifest_path.open() as f:
            return json.load(f)
    return None


class TestPythonScanner:
    """Test Python feature scanner accuracy."""

    def test_scan_patterns(self):
        """Verify Python scanner detects patterns."""
        result = python_scanner.scan()
        patterns = result["patterns"]

        # Should find major patterns
        expected_patterns = [
            "AutonomousAgent",
            "CollaborativeAgent",
            "ParallelAgent",
            "ReActAgent",
            "ReflectionAgent",
            "SequentialAgent",
        ]

        for pattern in expected_patterns:
            assert pattern in patterns, f"Missing pattern: {pattern}"

        # Should be non-empty
        assert len(patterns) >= 15, f"Expected at least 15 patterns, got {len(patterns)}"

    def test_scan_middleware(self):
        """Verify Python scanner detects middleware."""
        result = python_scanner.scan()
        middleware = result["middleware"]

        # Should find core middleware
        expected_middleware = [
            "TimeoutDecorator",
            "RetryDecorator",
            "RateLimiterDecorator",
            "CircuitBreakerDecorator",
        ]

        for mw in expected_middleware:
            assert mw in middleware, f"Missing middleware: {mw}"

        # Should find at least 7 middleware types
        assert len(middleware) >= 7, f"Expected at least 7 middleware, got {len(middleware)}"

    def test_scan_llm_adapters(self):
        """Verify Python scanner detects LLM adapters."""
        result = python_scanner.scan()
        adapters = result["llm_adapters"]

        # Should find major adapters
        expected_adapters = [
            "OpenAILLM",
            "AnthropicLLM",
            "BedrockLLM",
            "GeminiLLM",
        ]

        for adapter in expected_adapters:
            assert adapter in adapters, f"Missing adapter: {adapter}"

        # Should find at least 6 adapters
        assert len(adapters) >= 6, f"Expected at least 6 adapters, got {len(adapters)}"

    def test_scan_memory(self):
        """Verify Python scanner detects memory backends."""
        result = python_scanner.scan()
        memory = result["memory"]

        # Should find core memory backends
        expected_memory = [
            "EphemeralMemory",
            "VectorMemory",
            "RedisMemory",
        ]

        for mem in expected_memory:
            assert mem in memory, f"Missing memory backend: {mem}"

        # Should find at least 4 memory backends
        assert len(memory) >= 4, f"Expected at least 4 memory backends, got {len(memory)}"

    def test_no_false_positives(self):
        """Verify Python scanner doesn't detect non-existent features."""
        result = python_scanner.scan()
        patterns = result["patterns"]

        # Should NOT find these
        false_positives = ["NonExistentAgent", "FakeAgent", "TestAgent"]

        for fp in false_positives:
            assert fp not in patterns, f"False positive detected: {fp}"


class TestGoScanner:
    """Test Go feature scanner accuracy."""

    def test_scan_patterns(self):
        """Verify Go scanner detects patterns."""
        result = go_scanner.scan()
        patterns = result["patterns"]

        # Should find major patterns
        expected_patterns = [
            "AutonomousAgent",
            "ParallelAgent",
            "ReActAgent",
            "SequentialAgent",
        ]

        for pattern in expected_patterns:
            assert pattern in patterns, f"Missing pattern: {pattern}"

        # Should be non-empty
        assert len(patterns) >= 10, f"Expected at least 10 patterns, got {len(patterns)}"

    def test_scan_middleware(self):
        """Verify Go scanner detects middleware."""
        result = go_scanner.scan()
        middleware = result["middleware"]

        # Should find core middleware (including Config and Decorator)
        expected_middleware = [
            "TimeoutDecorator",
            "RetryDecorator",
            "RateLimiterDecorator",
            "CircuitBreakerDecorator",
        ]

        for mw in expected_middleware:
            assert mw in middleware, f"Missing middleware: {mw}"

        # Should find at least 10 middleware types (Config + Decorator for each)
        assert len(middleware) >= 10, f"Expected at least 10 middleware, got {len(middleware)}"

    def test_no_mock_types(self):
        """Verify Go scanner excludes mock types."""
        result = go_scanner.scan()
        patterns = result["patterns"]

        # Should NOT include mock types
        mock_types = ["MockAgent", "mockAgent", "mockReActAgent"]

        for mock in mock_types:
            assert mock not in patterns, f"Mock type detected: {mock}"


class TestTypeScriptScanner:
    """Test TypeScript feature scanner accuracy."""

    def test_scan_patterns(self):
        """Verify TypeScript scanner detects patterns."""
        result = typescript_scanner.scan()
        patterns = result["patterns"]

        # Should find major patterns
        expected_patterns = [
            "AutonomousAgent",
            "ParallelAgent",
            "ReActAgent",
            "SequentialAgent",
        ]

        for pattern in expected_patterns:
            assert pattern in patterns, f"Missing pattern: {pattern}"

        # Should be non-empty
        assert len(patterns) >= 10, f"Expected at least 10 patterns, got {len(patterns)}"

    def test_scan_memory(self):
        """Verify TypeScript scanner detects memory backends."""
        result = typescript_scanner.scan()
        memory = result["memory"]

        # Should find core memory backends
        expected_memory = [
            "InMemoryMemory",
            "VectorMemory",
            "RedisMemory",
            "EndlessMemory",  # TypeScript has this!
        ]

        for mem in expected_memory:
            assert mem in memory, f"Missing memory backend: {mem}"

    def test_no_base_classes(self):
        """Verify TypeScript scanner excludes base classes."""
        result = typescript_scanner.scan()
        patterns = result["patterns"]

        # Should NOT include base classes
        base_classes = ["Agent", "MultiAgent"]

        for base in base_classes:
            assert base not in patterns, f"Base class detected: {base}"


class TestFeatureManifest:
    """Test generated feature manifest structure and content."""

    def test_manifest_structure(self, feature_manifest):
        """Verify feature manifest has correct structure."""
        if not feature_manifest:
            pytest.skip("Feature manifest not generated yet")

        # Check required top-level keys
        assert "generated_at" in feature_manifest
        assert "version" in feature_manifest
        assert "languages" in feature_manifest
        assert "summary" in feature_manifest

        # Check version
        assert feature_manifest["version"] == "1.0"

    def test_all_languages_scanned(self, feature_manifest):
        """Verify all 6 languages are in manifest."""
        if not feature_manifest:
            pytest.skip("Feature manifest not generated yet")

        languages = feature_manifest["languages"]
        expected_langs = ["python", "go", "typescript", "rust", "cpp", "zig"]

        for lang in expected_langs:
            assert lang in languages, f"Missing language: {lang}"

    def test_language_schema(self, feature_manifest):
        """Verify each language has correct schema."""
        if not feature_manifest:
            pytest.skip("Feature manifest not generated yet")

        for lang, features in feature_manifest["languages"].items():
            # Each language should have these categories
            assert "patterns" in features
            assert "middleware" in features
            assert "llm_adapters" in features
            assert "memory" in features
            assert "techniques" in features

            # Each category should be a list
            assert isinstance(features["patterns"], list)
            assert isinstance(features["middleware"], list)
            assert isinstance(features["llm_adapters"], list)
            assert isinstance(features["memory"], list)
            assert isinstance(features["techniques"], list)

    def test_summary_completeness(self, feature_manifest):
        """Verify summary has all categories."""
        if not feature_manifest:
            pytest.skip("Feature manifest not generated yet")

        summary = feature_manifest["summary"]

        # Check categories
        expected_categories = [
            "patterns",
            "middleware",
            "llm_adapters",
            "memory",
            "techniques",
            "total",
        ]

        for category in expected_categories:
            assert category in summary, f"Missing category in summary: {category}"

    def test_python_go_typescript_have_features(self, feature_manifest):
        """Verify Python, Go, TypeScript have detected features."""
        if not feature_manifest:
            pytest.skip("Feature manifest not generated yet")

        summary = feature_manifest["summary"]["total"]

        # These languages should have features
        assert summary.get("python", 0) > 0, "Python should have features"
        assert summary.get("go", 0) > 0, "Go should have features"
        assert summary.get("typescript", 0) > 0, "TypeScript should have features"

    def test_no_duplicate_features(self, feature_manifest):
        """Verify no duplicate features within each language/category."""
        if not feature_manifest:
            pytest.skip("Feature manifest not generated yet")

        for lang, features in feature_manifest["languages"].items():
            for category, items in features.items():
                if isinstance(items, list):
                    # Check for duplicates
                    assert len(items) == len(set(items)), (
                        f"Duplicates found in {lang}.{category}: {items}"
                    )


@pytest.mark.parametrize(
    "scanner,expected_count",
    [
        (python_scanner, 40),  # Python should have at least 40 features
        (go_scanner, 35),  # Go should have at least 35 features
        (typescript_scanner, 30),  # TypeScript should have at least 30 features
    ],
)
def test_scanner_min_feature_count(scanner, expected_count):
    """Verify each scanner finds minimum number of features."""
    result = scanner.scan()

    total_features = sum(
        len(result.get(cat, []))
        for cat in ["patterns", "middleware", "llm_adapters", "memory", "techniques"]
    )

    assert total_features >= expected_count, (
        f"{scanner.__name__} found {total_features} features, expected >= {expected_count}"
    )
