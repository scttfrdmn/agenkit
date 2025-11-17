"""Security review agent - checks for vulnerabilities and security issues."""

import re
from datetime import datetime
from typing import List
from agenkit import Agent, Message
from agents.review_types import (
    ReviewResult,
    CodeIssue,
    CodeSubmission,
    IssueSeverity,
    IssueCategory,
)


class SecurityAgent(Agent):
    """
    Reviews code for security issues including:
    - SQL injection vulnerabilities
    - Command injection
    - Hardcoded secrets/credentials
    - Insecure cryptography
    - Path traversal
    """

    @property
    def name(self) -> str:
        return "SecurityAgent"

    async def process(self, message: Message) -> Message:
        """Process security review request."""
        submission = message.metadata.get("code_submission")

        if not isinstance(submission, CodeSubmission):
            return Message(
                role="assistant",
                content="Invalid code submission",
                metadata={"error": "Expected CodeSubmission in metadata"},
            )

        start_time = datetime.now()
        result = self._review_security(submission)
        result.execution_time = (datetime.now() - start_time).total_seconds()

        return Message(
            role="assistant",
            content=result.summary,
            metadata={"review_result": result},
        )

    def _review_security(self, submission: CodeSubmission) -> ReviewResult:
        """Perform security review."""
        issues: List[CodeIssue] = []
        lines = submission.get_lines()
        content = submission.content

        # Check for hardcoded secrets
        secret_patterns = [
            (r"password\s*=\s*['\"](?!<|{|\[)[^'\"]+['\"]", "Hardcoded password detected"),
            (r"api[_-]?key\s*=\s*['\"](?!<|{|\[)[^'\"]+['\"]", "Hardcoded API key detected"),
            (r"secret\s*=\s*['\"](?!<|{|\[)[^'\"]+['\"]", "Hardcoded secret detected"),
            (r"token\s*=\s*['\"](?!<|{|\[)[^'\"]+['\"]", "Hardcoded token detected"),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, message in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(
                        CodeIssue(
                            category=IssueCategory.SECURITY,
                            severity=IssueSeverity.CRITICAL,
                            message=message,
                            line_number=i,
                            file_path=submission.file_path,
                            code_snippet=line.strip(),
                            suggestion="Use environment variables or secret management system",
                        )
                    )

        # Check for SQL injection
        sql_injection_patterns = [
            r"execute\([^)]*\+",  # String concatenation in execute()
            r"executemany\([^)]*\+",
            r"cursor\.execute\([^)]*%",  # String formatting in SQL
        ]

        for i, line in enumerate(lines, 1):
            for pattern in sql_injection_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(
                        CodeIssue(
                            category=IssueCategory.SECURITY,
                            severity=IssueSeverity.CRITICAL,
                            message="Potential SQL injection vulnerability",
                            line_number=i,
                            file_path=submission.file_path,
                            code_snippet=line.strip(),
                            suggestion="Use parameterized queries with placeholders",
                        )
                    )

        # Check for command injection
        dangerous_functions = [
            r"os\.system\(",
            r"subprocess\.call\(",
            r"eval\(",
            r"exec\(",
        ]

        for i, line in enumerate(lines, 1):
            for pattern in dangerous_functions:
                if re.search(pattern, line):
                    issues.append(
                        CodeIssue(
                            category=IssueCategory.SECURITY,
                            severity=IssueSeverity.HIGH,
                            message=f"Potentially dangerous function: {pattern.replace('\\', '')}",
                            line_number=i,
                            file_path=submission.file_path,
                            code_snippet=line.strip(),
                            suggestion="Validate and sanitize all user inputs, use safe alternatives",
                        )
                    )

        # Check for insecure cryptography
        insecure_crypto = [
            (r"md5\(", "MD5 is cryptographically broken"),
            (r"sha1\(", "SHA1 is cryptographically weak"),
            (r"random\.", "Use secrets module for cryptographic randomness"),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, message in insecure_crypto:
                if re.search(pattern, line):
                    issues.append(
                        CodeIssue(
                            category=IssueCategory.SECURITY,
                            severity=IssueSeverity.MEDIUM,
                            message=message,
                            line_number=i,
                            file_path=submission.file_path,
                            code_snippet=line.strip(),
                            suggestion="Use SHA-256 or better, and secrets module for random values",
                        )
                    )

        # Check for path traversal
        if re.search(r"open\([^)]*\+", content):
            issues.append(
                CodeIssue(
                    category=IssueCategory.SECURITY,
                    severity=IssueSeverity.HIGH,
                    message="Potential path traversal vulnerability",
                    file_path=submission.file_path,
                    suggestion="Validate file paths and use os.path.basename()",
                )
            )

        # Calculate score
        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)
        medium_count = sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM)

        score = 10.0 - (critical_count * 4 + high_count * 2 + medium_count * 1)
        score = max(0.0, min(10.0, score))

        summary_parts = [f"Security Review: Found {len(issues)} issues"]
        if critical_count:
            summary_parts.append(f"{critical_count} CRITICAL")
        if high_count:
            summary_parts.append(f"{high_count} high")
        if medium_count:
            summary_parts.append(f"{medium_count} medium")

        summary = " - ".join(summary_parts)

        return ReviewResult(
            agent_name=self.name,
            issues=issues,
            summary=summary,
            overall_score=score,
            passed=critical_count == 0,
            metadata={"issues_by_severity": {"critical": critical_count, "high": high_count, "medium": medium_count}},
        )
