"""Correctness review agent - checks for bugs and logical errors."""

import re
from datetime import datetime
from typing import List
from agenkit import Agent, Message
from agents.review_types import ReviewResult, CodeIssue, CodeSubmission, IssueSeverity, IssueCategory


class CorrectnessAgent(Agent):
    """Reviews code for correctness issues like bugs and logic errors."""

    @property
    def name(self) -> str:
        return "CorrectnessAgent"

    async def process(self, message: Message) -> Message:
        submission = message.metadata.get("code_submission")
        if not isinstance(submission, CodeSubmission):
            return Message(role="assistant", content="Invalid", metadata={"error": "Expected CodeSubmission"})

        start_time = datetime.now()
        result = self._review_correctness(submission)
        result.execution_time = (datetime.now() - start_time).total_seconds()
        return Message(role="assistant", content=result.summary, metadata={"review_result": result})

    def _review_correctness(self, submission: CodeSubmission) -> ReviewResult:
        issues: List[CodeIssue] = []
        lines = submission.get_lines()

        # Check for unhandled exceptions
        for i, line in enumerate(lines, 1):
            if re.search(r"except:", line) and "pass" in (lines[i] if i < len(lines) else ""):
                issues.append(CodeIssue(
                    category=IssueCategory.CORRECTNESS, severity=IssueSeverity.HIGH,
                    message="Bare except clause with pass - silently ignores all errors",
                    line_number=i, file_path=submission.file_path, code_snippet=line.strip(),
                    suggestion="Handle specific exceptions or log errors"
                ))

        # Check for == in conditionals with assignments
        for i, line in enumerate(lines, 1):
            if re.search(r"if.*=\s*[^=]", line) and "==" not in line:
                issues.append(CodeIssue(
                    category=IssueCategory.CORRECTNESS, severity=IssueSeverity.HIGH,
                    message="Assignment in conditional - should use ==",
                    line_number=i, file_path=submission.file_path, code_snippet=line.strip(),
                    suggestion="Use == for comparison, = is assignment"
                ))

        # Check for mutable default arguments
        for i, line in enumerate(lines, 1):
            if match := re.search(r"def\s+\w+\([^)]*=\s*(\[\]|\{\})", line):
                issues.append(CodeIssue(
                    category=IssueCategory.CORRECTNESS, severity=IssueSeverity.HIGH,
                    message="Mutable default argument - will be shared across calls",
                    line_number=i, file_path=submission.file_path, code_snippet=line.strip(),
                    suggestion="Use None as default and create mutable object inside function"
                ))

        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)
        medium_count = sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM)

        score = 10.0 - (critical_count * 4 + high_count * 2 + medium_count * 1)
        score = max(0.0, min(10.0, score))

        summary = f"Correctness Review: Found {len(issues)} issues"
        if issues:
            summary += f" - {critical_count} critical, {high_count} high, {medium_count} medium"

        return ReviewResult(
            agent_name=self.name, issues=issues, summary=summary, overall_score=score,
            passed=critical_count == 0 and high_count == 0,
            metadata={"issues_by_severity": {"critical": critical_count, "high": high_count, "medium": medium_count}}
        )
