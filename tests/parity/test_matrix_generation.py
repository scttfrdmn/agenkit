"""Tests for parity matrix generation.

Validates that matrix generator correctly combines feature manifest
and test reports to produce accurate parity matrices.
"""

from pathlib import Path

import pytest

from scripts.parity import matrix_generator


@pytest.fixture
def feature_manifest():
    """Load feature manifest if it exists."""
    try:
        return matrix_generator.load_feature_manifest()
    except FileNotFoundError:
        pytest.skip("Feature manifest not generated yet")


@pytest.fixture
def test_report():
    """Load test report if it exists."""
    return matrix_generator.load_test_report()


class TestMatrixDataGeneration:
    """Test matrix data structure generation."""

    def test_build_matrix_data_structure(self, feature_manifest, test_report):
        """Verify matrix data has correct structure."""
        matrix_data = matrix_generator.build_matrix_data(feature_manifest, test_report)

        # Check required keys
        assert "generated_at" in matrix_data
        assert "languages" in matrix_data
        assert "categories" in matrix_data
        assert "matrix_rows" in matrix_data
        assert "summary_stats" in matrix_data
        assert "category_summaries" in matrix_data
        assert "has_test_data" in matrix_data

        # Verify languages list
        expected_langs = ["python", "go", "typescript", "rust", "cpp", "zig"]
        assert matrix_data["languages"] == expected_langs

        # Verify categories list
        expected_cats = ["patterns", "middleware", "llm_adapters", "memory"]
        assert matrix_data["categories"] == expected_cats

    def test_matrix_rows_format(self, feature_manifest, test_report):
        """Verify matrix rows have correct format."""
        matrix_data = matrix_generator.build_matrix_data(feature_manifest, test_report)

        for row in matrix_data["matrix_rows"]:
            # Each row should have category, feature, and languages
            assert "category" in row
            assert "feature" in row
            assert "languages" in row

            # Languages should have status for all 6 languages
            assert len(row["languages"]) == 6

            # Status should be either ✅ or ❌
            for lang, status in row["languages"].items():
                assert status in ["✅", "❌"], f"Invalid status: {status}"

    def test_summary_stats_format(self, feature_manifest, test_report):
        """Verify summary stats have correct format."""
        matrix_data = matrix_generator.build_matrix_data(feature_manifest, test_report)

        # Should have stats for all 6 languages
        assert len(matrix_data["summary_stats"]) == 6

        for stat in matrix_data["summary_stats"]:
            assert "language" in stat
            assert "total_features" in stat
            assert "parity_percent" in stat
            assert "test_count" in stat

            # Parity percent should be between 0 and 100
            assert 0 <= stat["parity_percent"] <= 100

    def test_category_summaries(self, feature_manifest, test_report):
        """Verify category summaries have correct counts."""
        matrix_data = matrix_generator.build_matrix_data(feature_manifest, test_report)

        for summary in matrix_data["category_summaries"]:
            assert "category" in summary
            assert "counts" in summary

            # Should have counts for all 6 languages
            assert len(summary["counts"]) == 6

            # All counts should be non-negative
            for count in summary["counts"].values():
                assert count >= 0


class TestMatrixMarkdownGeneration:
    """Test matrix markdown generation."""

    def test_generate_feature_matrix(self, feature_manifest, test_report):
        """Verify matrix markdown is generated."""
        matrix_md = matrix_generator.generate_feature_matrix(feature_manifest, test_report)

        # Should be non-empty string
        assert isinstance(matrix_md, str)
        assert len(matrix_md) > 0

        # Should contain expected sections
        assert "# Feature Parity Matrix" in matrix_md
        assert "## Summary Statistics" in matrix_md
        assert "## Feature Matrix by Category" in matrix_md

    def test_matrix_contains_language_names(self, feature_manifest, test_report):
        """Verify matrix includes all language names."""
        matrix_md = matrix_generator.generate_feature_matrix(feature_manifest, test_report)

        languages = ["Python", "Go", "TypeScript", "Rust", "C++", "Zig"]

        for lang in languages:
            assert lang in matrix_md, f"Language {lang} not found in matrix"

    def test_matrix_contains_status_indicators(self, feature_manifest, test_report):
        """Verify matrix uses status indicators."""
        matrix_md = matrix_generator.generate_feature_matrix(feature_manifest, test_report)

        # Should contain status indicators
        assert "✅" in matrix_md  # Implemented
        assert "❌" in matrix_md  # Missing


class TestGapAnalysis:
    """Test gap analysis generation."""

    def test_generate_gap_analysis(self, feature_manifest):
        """Verify gap analysis is generated."""
        gap_md = matrix_generator.generate_gap_analysis(feature_manifest)

        # Should be non-empty string
        assert isinstance(gap_md, str)
        assert len(gap_md) > 0

        # Should contain expected sections
        assert "# Feature Gap Analysis" in gap_md

    def test_gap_analysis_shows_missing_features(self, feature_manifest):
        """Verify gap analysis identifies missing features."""
        gap_md = matrix_generator.generate_gap_analysis(feature_manifest)

        # If TypeScript has gaps (which it does), they should be listed
        if (
            feature_manifest["summary"]["total"]["typescript"]
            < feature_manifest["summary"]["total"]["python"]
        ):
            assert "## Typescript Gaps" in gap_md

    def test_gap_analysis_excludes_python(self, feature_manifest):
        """Verify gap analysis doesn't include Python (baseline)."""
        gap_md = matrix_generator.generate_gap_analysis(feature_manifest)

        # Python is the baseline, so shouldn't have a gaps section
        assert "## Python Gaps" not in gap_md


class TestFileOutput:
    """Test file output generation."""

    def test_matrix_file_created(self):
        """Verify matrix file is created in correct location."""
        matrix_path = Path("docs/parity/FEATURE_MATRIX.md")

        # File should exist (created by matrix_generator.py)
        if matrix_path.exists():
            assert matrix_path.is_file()
            assert matrix_path.stat().st_size > 0
        else:
            pytest.skip("Matrix not generated yet")

    def test_gap_analysis_file_created(self):
        """Verify gap analysis file is created."""
        gap_path = Path("docs/parity/GAPS_ANALYSIS.md")

        # File should exist (created by matrix_generator.py)
        if gap_path.exists():
            assert gap_path.is_file()
            assert gap_path.stat().st_size > 0
        else:
            pytest.skip("Gap analysis not generated yet")

    def test_matrix_file_format(self):
        """Verify matrix file is valid markdown."""
        matrix_path = Path("docs/parity/FEATURE_MATRIX.md")

        if not matrix_path.exists():
            pytest.skip("Matrix not generated yet")

        content = matrix_path.read_text()

        # Should start with header
        assert content.startswith("# Feature Parity Matrix")

        # Should contain markdown tables
        assert "|" in content
        assert "---" in content


class TestDataIntegrity:
    """Test data integrity and consistency."""

    def test_feature_counts_match_manifest(self, feature_manifest, test_report):
        """Verify matrix feature counts match manifest."""
        matrix_data = matrix_generator.build_matrix_data(feature_manifest, test_report)

        # For each language, total from summary_stats should match manifest
        for stat in matrix_data["summary_stats"]:
            lang = stat["language"]
            total = stat["total_features"]

            manifest_total = feature_manifest["summary"]["total"].get(lang, 0)

            assert total == manifest_total, (
                f"{lang}: matrix shows {total} but manifest has {manifest_total}"
            )

    def test_parity_percentages_calculated_correctly(self, feature_manifest, test_report):
        """Verify parity percentages are calculated correctly."""
        matrix_data = matrix_generator.build_matrix_data(feature_manifest, test_report)

        python_total = next(
            s["total_features"] for s in matrix_data["summary_stats"] if s["language"] == "python"
        )

        for stat in matrix_data["summary_stats"]:
            if python_total > 0:
                expected_parity = round(stat["total_features"] / python_total * 100, 1)
                assert abs(stat["parity_percent"] - expected_parity) < 0.1, (
                    f"{stat['language']}: parity mismatch"
                )
