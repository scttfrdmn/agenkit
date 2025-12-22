"""Performance review agent - checks for performance issues."""

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


class PerformanceAgent(Agent):
    """Reviews code for performance issues."""

    @property
    def name(self) -> str:
        return "PerformanceAgent"

    async def process(self, message: Message) -> Message:
        submission = message.metadata.get("code_submission")
        if not isinstance(submission, CodeSubmission):
            return Message(
                role="assistant",
                content="Invalid code submission",
                metadata={"error": "Expected CodeSubmission"},
            )

        start_time = datetime.now()
        result = self._review_performance(submission)
        result.execution_time = (datetime.now() - start_time).total_seconds()

        return Message(role="assistant", content=result.summary, metadata={"review_result": result})

    def _review_performance(self, submission: CodeSubmission) -> ReviewResult:
        issues: list[CodeIssue] = []
        lines = submission.get_lines()

        # Check for nested loops
        for i, line in enumerate(lines, 1):
            if re.search(r"for\s+\w+\s+in", line):
                # Check if we're inside another loop (simplified)
                if i > 1 and any(
                    re.search(r"for\s+\w+\s+in", lines[j]) for j in range(max(0, i - 10), i - 1)
                ):
                    issues.append(
                        CodeIssue(
                            category=IssueCategory.PERFORMANCE,
                            severity=IssueSeverity.MEDIUM,
                            message="Nested loop detected - O(n²) or worse complexity",
                            line_number=i,
                            file_path=submission.file_path,
                            code_snippet=line.strip(),
                            suggestion="Consider using hash maps or alternative algorithms",
                        )
                    )

        # Check for repeated list operations
        for i, line in enumerate(lines, 1):
            if re.search(r"\.append\(.*\)\s*$", line) and "for" in "".join(
                lines[max(0, i - 3) : i]
            ):
                issues.append(
                    CodeIssue(
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.LOW,
                        message="Repeated list.append() in loop",
                        line_number=i,
                        file_path=submission.file_path,
                        suggestion="Consider list comprehension or pre-allocation",
                    )
                )

        # Check for string concatenation in loops
        for i, line in enumerate(lines, 1):
            if re.search(r"\+=\s*['\"]", line) and "for" in "".join(lines[max(0, i - 3) : i]):
                issues.append(
                    CodeIssue(
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.MEDIUM,
                        message="String concatenation in loop is inefficient",
                        line_number=i,
                        file_path=submission.file_path,
                        code_snippet=line.strip(),
                        suggestion="Use list and join(), or io.StringIO()",
                    )
                )

        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)
        medium_count = sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM)
        low_count = sum(1 for i in issues if i.severity == IssueSeverity.LOW)

        score = 10.0 - (critical_count * 3 + high_count * 2 + medium_count * 1 + low_count * 0.5)
        score = max(0.0, min(10.0, score))

        summary = f"Performance Review: Found {len(issues)} issues"
        if issues:
            summary += f" - {critical_count} critical, {high_count} high, {medium_count} medium, {low_count} low"

        return ReviewResult(
            agent_name=self.name,
            issues=issues,
            summary=summary,
            overall_score=score,
            passed=high_count == 0 and critical_count == 0,
            metadata={
                "issues_by_severity": {
                    "critical": critical_count,
                    "high": high_count,
                    "medium": medium_count,
                    "low": low_count,
                }
            },
        )
