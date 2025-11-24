"""Style review agent - checks code formatting, naming, and conventions."""

import re
from datetime import datetime

from agenkit import Agent, Message
from agents.review_types import (
    CodeIssue,
    CodeSubmission,
    IssueCategory,
    IssueSeverity,
    ReviewResult,
)


class StyleAgent(Agent):
    """
    Reviews code for style issues including:
    - Naming conventions (camelCase, snake_case, etc.)
    - Line length
    - Indentation consistency
    - Trailing whitespace
    - Comment style
    """

    @property
    def name(self) -> str:
        return "StyleAgent"

    async def process(self, message: Message) -> Message:
        """Process style review request."""
        submission = message.metadata.get("code_submission")

        if not isinstance(submission, CodeSubmission):
            return Message(
                role="assistant",
                content="Invalid code submission",
                metadata={"error": "Expected CodeSubmission in metadata"},
            )

        start_time = datetime.now()
        result = self._review_style(submission)
        result.execution_time = (datetime.now() - start_time).total_seconds()

        return Message(
            role="assistant",
            content=result.summary,
            metadata={"review_result": result},
        )

    def _review_style(self, submission: CodeSubmission) -> ReviewResult:
        """Perform style review."""
        issues: list[CodeIssue] = []
        lines = submission.get_lines()

        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(
                    CodeIssue(
                        category=IssueCategory.STYLE,
                        severity=IssueSeverity.LOW,
                        message=f"Line exceeds 120 characters ({len(line)} chars)",
                        line_number=i,
                        file_path=submission.file_path,
                        suggestion="Consider breaking into multiple lines",
                    )
                )

        # Check trailing whitespace
        for i, line in enumerate(lines, 1):
            if line.rstrip() != line and line.strip():  # Has trailing whitespace
                issues.append(
                    CodeIssue(
                        category=IssueCategory.STYLE,
                        severity=IssueSeverity.LOW,
                        message="Trailing whitespace detected",
                        line_number=i,
                        file_path=submission.file_path,
                        suggestion="Remove trailing whitespace",
                    )
                )

        # Check naming conventions (Python example)
        if submission.language == "python":
            # Check for camelCase function names (should be snake_case)
            for i, line in enumerate(lines, 1):
                if match := re.search(r"def ([a-z]+[A-Z]\w+)\(", line):
                    func_name = match.group(1)
                    issues.append(
                        CodeIssue(
                            category=IssueCategory.STYLE,
                            severity=IssueSeverity.MEDIUM,
                            message=f"Function '{func_name}' uses camelCase, should use snake_case",
                            line_number=i,
                            file_path=submission.file_path,
                            code_snippet=line.strip(),
                            suggestion=f"Rename to '{self._to_snake_case(func_name)}'",
                        )
                    )

            # Check for snake_case class names (should be PascalCase)
            for i, line in enumerate(lines, 1):
                if match := re.search(r"class ([a-z]+_\w+)", line):
                    class_name = match.group(1)
                    issues.append(
                        CodeIssue(
                            category=IssueCategory.STYLE,
                            severity=IssueSeverity.MEDIUM,
                            message=f"Class '{class_name}' uses snake_case, should use PascalCase",
                            line_number=i,
                            file_path=submission.file_path,
                            code_snippet=line.strip(),
                            suggestion=f"Rename to '{self._to_pascal_case(class_name)}'",
                        )
                    )

        # Check indentation consistency
        indent_counts = {}
        for i, line in enumerate(lines, 1):
            if line and not line[0].isspace():
                continue
            leading_spaces = len(line) - len(line.lstrip())
            if leading_spaces > 0:
                indent_counts[leading_spaces] = indent_counts.get(leading_spaces, 0) + 1

        if len(indent_counts) > 2:  # Mixed indentation
            issues.append(
                CodeIssue(
                    category=IssueCategory.STYLE,
                    severity=IssueSeverity.HIGH,
                    message=f"Inconsistent indentation detected: {list(indent_counts.keys())} spaces used",
                    file_path=submission.file_path,
                    suggestion="Use consistent indentation (2 or 4 spaces)",
                )
            )

        # Calculate score
        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)
        medium_count = sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM)
        low_count = sum(1 for i in issues if i.severity == IssueSeverity.LOW)

        # Score: 10 - (critical*3 + high*2 + medium*1 + low*0.5)
        score = 10.0 - (critical_count * 3 + high_count * 2 + medium_count * 1 + low_count * 0.5)
        score = max(0.0, min(10.0, score))

        # Generate summary
        summary_parts = [f"Style Review: Found {len(issues)} issues"]
        if critical_count:
            summary_parts.append(f"{critical_count} critical")
        if high_count:
            summary_parts.append(f"{high_count} high")
        if medium_count:
            summary_parts.append(f"{medium_count} medium")
        if low_count:
            summary_parts.append(f"{low_count} low")

        summary = " - ".join(summary_parts)

        return ReviewResult(
            agent_name=self.name,
            issues=issues,
            summary=summary,
            overall_score=score,
            passed=critical_count == 0 and high_count == 0,
            metadata={
                "issues_by_severity": {
                    "critical": critical_count,
                    "high": high_count,
                    "medium": medium_count,
                    "low": low_count,
                }
            },
        )

    def _to_snake_case(self, name: str) -> str:
        """Convert camelCase to snake_case."""
        return re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")

    def _to_pascal_case(self, name: str) -> str:
        """Convert snake_case to PascalCase."""
        return "".join(word.capitalize() for word in name.split("_"))
