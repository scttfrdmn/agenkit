"""
Validator for AGENTS.md files.

This module provides validation functions to check AGENTS.md files for
completeness and correctness.
"""

from dataclasses import dataclass, field
from enum import Enum

from .types import AgentsMdDocument, SectionType


class IssueSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """
    A validation issue found in an AGENTS.md file.

    Attributes:
        severity: Issue severity level
        message: Human-readable message
        section: Optional section where issue was found
        line_number: Optional line number
    """

    severity: IssueSeverity
    message: str
    section: str | None = None
    line_number: int | None = None

    def __str__(self) -> str:
        """String representation of issue."""
        parts = [f"[{self.severity.value.upper()}]", self.message]
        if self.section:
            parts.append(f"(section: {self.section})")
        if self.line_number:
            parts.append(f"(line: {self.line_number})")
        return " ".join(parts)


@dataclass
class ValidationResult:
    """
    Result of validating an AGENTS.md file.

    Attributes:
        is_valid: Whether file passed validation
        issues: List of validation issues
        recommendations: List of recommended improvements
    """

    is_valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def add_error(
        self, message: str, section: str | None = None, line_number: int | None = None
    ) -> None:
        """Add an error (makes validation fail)."""
        self.is_valid = False
        self.issues.append(
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                message=message,
                section=section,
                line_number=line_number,
            )
        )

    def add_warning(
        self, message: str, section: str | None = None, line_number: int | None = None
    ) -> None:
        """Add a warning (doesn't fail validation)."""
        self.issues.append(
            ValidationIssue(
                severity=IssueSeverity.WARNING,
                message=message,
                section=section,
                line_number=line_number,
            )
        )

    def add_info(
        self, message: str, section: str | None = None, line_number: int | None = None
    ) -> None:
        """Add an informational message."""
        self.issues.append(
            ValidationIssue(
                severity=IssueSeverity.INFO,
                message=message,
                section=section,
                line_number=line_number,
            )
        )

    def has_errors(self) -> bool:
        """Check if result has errors."""
        return any(i.severity == IssueSeverity.ERROR for i in self.issues)

    def has_warnings(self) -> bool:
        """Check if result has warnings."""
        return any(i.severity == IssueSeverity.WARNING for i in self.issues)

    def __str__(self) -> str:
        """String representation of result."""
        status = "PASS" if self.is_valid else "FAIL"
        error_count = sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)
        warning_count = sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)
        return f"Validation {status}: {error_count} errors, {warning_count} warnings"


def validate_agents_md(doc: AgentsMdDocument, strict: bool = False) -> ValidationResult:
    """
    Validate an AGENTS.md document.

    Checks for:
    - Recommended sections present
    - Sections not empty
    - Proper markdown structure
    - Completeness of documentation

    Args:
        doc: Document to validate
        strict: If True, missing recommended sections are errors (default: warnings)

    Returns:
        ValidationResult with issues found

    Example:
        ```python
        doc = parse_agents_md("./AGENTS.md")
        result = validate_agents_md(doc)

        if not result.is_valid:
            for issue in result.issues:
                print(issue)
        ```
    """
    result = ValidationResult()

    # Check for empty document
    if not doc.sections:
        result.add_error("Document has no sections")
        return result

    # Check for recommended sections
    recommended = [
        (SectionType.SETUP, "Setup instructions help agents configure the project"),
        (SectionType.CODE_STYLE, "Code style guidelines ensure consistent code"),
        (SectionType.TESTING, "Testing procedures help maintain quality"),
    ]

    for section_type, reason in recommended:
        if not doc.has_section(section_type):
            if strict:
                result.add_error(f"Missing recommended section: {section_type.value}")
            else:
                result.add_warning(f"Missing recommended section: {section_type.value}. {reason}")

    # Check for empty sections
    for section in doc.sections:
        if section.is_empty():
            result.add_warning(f"Empty section: {section.heading}", section=section.heading)

    # Check for very short sections (likely incomplete)
    for section in doc.sections:
        if 0 < len(section.content) < 50:
            result.add_info(
                f"Very short section (may need more detail): {section.heading}",
                section=section.heading,
            )

    # Add recommendations
    if not doc.has_section(SectionType.ARCHITECTURE):
        result.recommendations.append(
            "Consider adding an Architecture section to document system design"
        )

    if not doc.has_section(SectionType.PATTERNS):
        result.recommendations.append(
            "Consider adding a Patterns section to document common patterns"
        )

    # Check for good practices
    setup_section = doc.get_section(SectionType.SETUP)
    if setup_section and "```" not in setup_section.content:
        result.recommendations.append(
            "Setup section should include code examples (use markdown code blocks)"
        )

    return result
