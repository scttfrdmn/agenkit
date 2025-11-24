"""Shared types for code review system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class IssueSeverity(Enum):
    """Severity level of a code issue."""

    CRITICAL = "critical"  # Must fix immediately
    HIGH = "high"  # Should fix soon
    MEDIUM = "medium"  # Should address
    LOW = "low"  # Nice to have
    INFO = "info"  # Informational only


class IssueCategory(Enum):
    """Category of code issue."""

    STYLE = "style"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CORRECTNESS = "correctness"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"


@dataclass
class CodeIssue:
    """A specific issue found during code review."""

    category: IssueCategory
    severity: IssueSeverity
    message: str
    line_number: int | None = None
    file_path: str | None = None
    code_snippet: str | None = None
    suggestion: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        location = f" at {self.file_path}:{self.line_number}" if self.line_number else ""
        return f"[{self.severity.value.upper()}] {self.message}{location}"


@dataclass
class ReviewResult:
    """
    Result from a code review agent.

    Contains the agent's findings, overall assessment, and metadata.
    """

    agent_name: str
    issues: list[CodeIssue] = field(default_factory=list)
    summary: str = ""
    overall_score: float = 0.0  # 0.0 to 10.0
    passed: bool = True
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_issues_by_severity(self, severity: IssueSeverity) -> list[CodeIssue]:
        """Get all issues of a specific severity."""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_critical_count(self) -> int:
        """Get number of critical issues."""
        return len(self.get_issues_by_severity(IssueSeverity.CRITICAL))

    def get_high_count(self) -> int:
        """Get number of high severity issues."""
        return len(self.get_issues_by_severity(IssueSeverity.HIGH))

    def get_total_issues(self) -> int:
        """Get total number of issues."""
        return len(self.issues)

    def __repr__(self) -> str:
        return (
            f"ReviewResult(agent={self.agent_name}, "
            f"issues={len(self.issues)}, "
            f"score={self.overall_score:.1f}, "
            f"passed={self.passed})"
        )


@dataclass
class CodeSubmission:
    """
    Code to be reviewed.

    Can be a single file, multiple files, or a diff.
    """

    content: str
    file_path: str | None = None
    language: str | None = None
    diff_mode: bool = False  # Whether content is a git diff
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_lines(self) -> list[str]:
        """Get code as list of lines."""
        return self.content.split("\n")

    def get_line_count(self) -> int:
        """Get number of lines."""
        return len(self.get_lines())

    def __repr__(self) -> str:
        lines = self.get_line_count()
        return f"CodeSubmission(lines={lines}, language={self.language}, file={self.file_path})"
