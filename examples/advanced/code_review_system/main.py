"""
Multi-Agent Code Review System with Debate and Consensus

This example demonstrates advanced multi-agent patterns:
- Debate Pattern: Multiple specialized reviewers argue perspectives
- Consensus Building: Severity-based agreement thresholds
- Agents-as-Tools: Linters and formatters as agent tools
- Reflection: Self-critique of review quality

Usage:
    python main.py review path/to/file.py
    python main.py review --diff HEAD~1
    python main.py review --pr 123 --repo owner/repo
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from agenkit.interfaces import Agent, Message


class Severity(Enum):
    """Issue severity levels."""

    BLOCKER = "blocker"  # Must fix - blocks approval
    MAJOR = "major"  # Should fix - significant concern
    MINOR = "minor"  # Nice to fix - suggestion
    INFO = "info"  # Informational only


class ReviewDecision(Enum):
    """Review decision outcomes."""

    APPROVE = "approve"  # No blockers, ready to merge
    APPROVE_WITH_COMMENTS = "approve_with_comments"  # Minor suggestions only
    REQUEST_CHANGES = "request_changes"  # Blockers or major issues present
    REJECT = "reject"  # Fundamental issues, needs redesign


class ReviewerType(Enum):
    """Types of code reviewers."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"


@dataclass
class CodeIssue:
    """A code review issue found by a reviewer."""

    severity: Severity
    reviewer: str  # Which reviewer found it
    title: str
    description: str
    line_number: int | None = None
    code_snippet: str | None = None
    suggestion: str | None = None
    confidence: float = 0.8  # 0.0-1.0


@dataclass
class ReviewerOpinion:
    """A reviewer's opinion on the code."""

    reviewer: ReviewerType
    issues: list[CodeIssue]
    overall_assessment: str
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class DebateRound:
    """A single round of debate between reviewers."""

    round_number: int
    opinions: list[ReviewerOpinion]
    rebuttals: dict[str, str]  # reviewer_name -> rebuttal text
    areas_of_agreement: list[str]
    areas_of_disagreement: list[str]


@dataclass
class ReviewReport:
    """Final code review report."""

    decision: ReviewDecision
    blocker_issues: list[CodeIssue]
    major_issues: list[CodeIssue]
    minor_issues: list[CodeIssue]
    info_issues: list[CodeIssue]
    debate_rounds: list[DebateRound]
    consensus_summary: str
    reviewers: list[str]
    confidence_score: float
    timestamp: datetime
    metadata: dict[str, Any]

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = []
        lines.append("# Code Review Report")
        lines.append(f"\n**Decision**: {self.decision.value.upper().replace('_', ' ')}")
        lines.append(f"**Timestamp**: {self.timestamp.isoformat()}")
        lines.append(f"**Reviewers**: {', '.join(self.reviewers)}")
        lines.append(f"**Confidence**: {self.confidence_score:.2f}")

        # Summary
        lines.append(f"\n## Summary\n\n{self.consensus_summary}")

        # Blockers
        if self.blocker_issues:
            lines.append(f"\n## 🚫 Blocker Issues ({len(self.blocker_issues)})")
            for i, issue in enumerate(self.blocker_issues, 1):
                lines.append(f"\n### {i}. {issue.title}")
                lines.append(f"**Reviewer**: {issue.reviewer}")
                if issue.line_number:
                    lines.append(f"**Line**: {issue.line_number}")
                lines.append(f"\n{issue.description}")
                if issue.suggestion:
                    lines.append(f"\n**Suggestion**: {issue.suggestion}")

        # Major issues
        if self.major_issues:
            lines.append(f"\n## ⚠️ Major Issues ({len(self.major_issues)})")
            for i, issue in enumerate(self.major_issues, 1):
                lines.append(f"\n### {i}. {issue.title}")
                lines.append(f"**Reviewer**: {issue.reviewer} | **Line**: {issue.line_number or 'N/A'}")
                lines.append(f"\n{issue.description}")

        # Minor issues
        if self.minor_issues:
            lines.append(f"\n## 💡 Minor Suggestions ({len(self.minor_issues)})")
            for i, issue in enumerate(self.minor_issues, 1):
                lines.append(f"- **{issue.title}** (Line {issue.line_number or 'N/A'}): {issue.description}")

        # Debate summary
        if self.debate_rounds:
            lines.append(f"\n## 🗣️ Debate Summary ({len(self.debate_rounds)} rounds)")
            for debate in self.debate_rounds:
                lines.append(f"\n### Round {debate.round_number}")
                if debate.areas_of_agreement:
                    lines.append(f"**Agreement**: {', '.join(debate.areas_of_agreement)}")
                if debate.areas_of_disagreement:
                    lines.append(f"**Disagreement**: {', '.join(debate.areas_of_disagreement)}")

        return "\n".join(lines)


class MockReviewerAgent(Agent):
    """
    Mock reviewer agent for demonstration.

    In production, this would:
    - Use LLM to analyze code
    - Run static analysis tools
    - Check against security/performance/maintainability guidelines
    """

    def __init__(self, reviewer_type: ReviewerType, agent_id: str):
        self.reviewer_type = reviewer_type
        self.agent_id = agent_id
        self._name = f"{reviewer_type.value}_reviewer"

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["code_review", "issue_detection", "debate"]

    async def process(self, message: Message) -> Message:
        """
        Simulate code review process.

        In production, would:
        1. Parse code from message
        2. Run analysis based on reviewer type
        3. Generate issues with severity, line numbers, suggestions
        4. Return structured ReviewerOpinion
        """
        code = message.content

        # Simulate finding issues based on reviewer type
        issues = self._simulate_review(code)

        opinion = ReviewerOpinion(
            reviewer=self.reviewer_type,
            issues=issues,
            overall_assessment=self._generate_assessment(issues),
            confidence=0.85,
        )

        response_content = json.dumps(
            {
                "reviewer": self.reviewer_type.value,
                "issues": [
                    {
                        "severity": i.severity.value,
                        "title": i.title,
                        "description": i.description,
                        "line_number": i.line_number,
                        "suggestion": i.suggestion,
                        "confidence": i.confidence,
                    }
                    for i in issues
                ],
                "overall_assessment": opinion.overall_assessment,
                "confidence": opinion.confidence,
            },
            indent=2,
        )

        return Message(
            role="assistant",
            content=response_content,
            metadata={
                "reviewer_type": self.reviewer_type.value,
                "issues_count": len(issues),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    def _simulate_review(self, code: str) -> list[CodeIssue]:
        """Simulate finding issues based on reviewer type."""
        issues = []

        if self.reviewer_type == ReviewerType.SECURITY:
            # Security reviewer finds vulnerabilities
            if "password" in code.lower() or "secret" in code.lower():
                issues.append(
                    CodeIssue(
                        severity=Severity.BLOCKER,
                        reviewer=self.reviewer_type.value,
                        title="Potential secret in code",
                        description="Hardcoded credentials detected. Use environment variables or secret management.",
                        line_number=10,
                        suggestion="Use os.environ['SECRET_KEY'] or a secrets manager",
                        confidence=0.9,
                    )
                )
            if "sql" in code.lower() and ("+" in code or "%" in code):
                issues.append(
                    CodeIssue(
                        severity=Severity.BLOCKER,
                        reviewer=self.reviewer_type.value,
                        title="SQL injection vulnerability",
                        description="String concatenation in SQL query. Use parameterized queries.",
                        line_number=25,
                        suggestion="Use prepared statements or ORM",
                        confidence=0.85,
                    )
                )

        elif self.reviewer_type == ReviewerType.PERFORMANCE:
            # Performance reviewer finds inefficiencies
            if "for" in code and "for" in code[code.index("for") + 3 :]:
                issues.append(
                    CodeIssue(
                        severity=Severity.MAJOR,
                        reviewer=self.reviewer_type.value,
                        title="Nested loops detected",
                        description="O(n²) complexity. Consider optimizing with hash map or set.",
                        line_number=15,
                        suggestion="Use dictionary lookup for O(n) complexity",
                        confidence=0.8,
                    )
                )
            if "sleep" in code.lower():
                issues.append(
                    CodeIssue(
                        severity=Severity.MINOR,
                        reviewer=self.reviewer_type.value,
                        title="Blocking sleep call",
                        description="Sleep blocks execution. Consider async/await or event-driven approach.",
                        line_number=30,
                        suggestion="Use asyncio.sleep() or event loop",
                        confidence=0.7,
                    )
                )

        elif self.reviewer_type == ReviewerType.MAINTAINABILITY:
            # Maintainability reviewer finds readability issues
            if len(code) > 500:
                issues.append(
                    CodeIssue(
                        severity=Severity.MAJOR,
                        reviewer=self.reviewer_type.value,
                        title="Function too long",
                        description="Function exceeds 100 lines. Consider extracting helper functions.",
                        line_number=1,
                        suggestion="Break into smaller, focused functions",
                        confidence=0.75,
                    )
                )
            if code.count("TODO") > 0 or code.count("FIXME") > 0:
                issues.append(
                    CodeIssue(
                        severity=Severity.MINOR,
                        reviewer=self.reviewer_type.value,
                        title="TODO/FIXME comments present",
                        description="Unresolved TODO/FIXME comments. Address before merging.",
                        line_number=5,
                        confidence=0.9,
                    )
                )

        return issues

    def _generate_assessment(self, issues: list[CodeIssue]) -> str:
        """Generate overall assessment based on issues found."""
        blocker_count = sum(1 for i in issues if i.severity == Severity.BLOCKER)
        major_count = sum(1 for i in issues if i.severity == Severity.MAJOR)

        if blocker_count > 0:
            return f"REJECT: {blocker_count} blocking issue(s) must be fixed."
        elif major_count > 2:
            return f"REQUEST_CHANGES: {major_count} major issues should be addressed."
        elif major_count > 0:
            return f"APPROVE_WITH_COMMENTS: {major_count} major suggestion(s)."
        else:
            return "APPROVE: Code looks good!"


class DebateModerator:
    """
    Moderates debate between reviewers to reach consensus.

    Implements structured debate pattern with rounds and rebuttals.
    """

    def __init__(self, max_rounds: int = 2):
        self.max_rounds = max_rounds

    async def moderate_debate(
        self, opinions: list[ReviewerOpinion]
    ) -> list[DebateRound]:
        """
        Facilitate debate rounds between reviewers.

        Args:
            opinions: Initial opinions from all reviewers

        Returns:
            List of debate rounds with rebuttals and consensus attempts
        """
        debates = []

        # Round 1: Present all opinions
        round1 = DebateRound(
            round_number=1,
            opinions=opinions,
            rebuttals={},
            areas_of_agreement=self._find_agreement(opinions),
            areas_of_disagreement=self._find_disagreement(opinions),
        )
        debates.append(round1)

        # Additional rounds for rebuttals (if configured)
        for round_num in range(2, self.max_rounds + 1):
            # In production, would ask each reviewer to respond to others
            # For demo, we just track that debate happened
            rebuttals = {
                opinion.reviewer.value: f"Round {round_num} rebuttal from {opinion.reviewer.value}"
                for opinion in opinions
            }

            round_n = DebateRound(
                round_number=round_num,
                opinions=opinions,
                rebuttals=rebuttals,
                areas_of_agreement=self._find_agreement(opinions),
                areas_of_disagreement=self._find_disagreement(opinions),
            )
            debates.append(round_n)

        return debates

    def _find_agreement(self, opinions: list[ReviewerOpinion]) -> list[str]:
        """Find issues that multiple reviewers agree on."""
        # Group issues by title (normalized)
        issue_counts: dict[str, int] = {}
        for opinion in opinions:
            for issue in opinion.issues:
                normalized_title = issue.title.lower().strip()
                issue_counts[normalized_title] = issue_counts.get(normalized_title, 0) + 1

        # Agreement = 2+ reviewers found same issue
        agreements = [title for title, count in issue_counts.items() if count >= 2]
        return agreements

    def _find_disagreement(self, opinions: list[ReviewerOpinion]) -> list[str]:
        """Find issues that only one reviewer flagged."""
        issue_counts: dict[str, int] = {}
        for opinion in opinions:
            for issue in opinion.issues:
                normalized_title = issue.title.lower().strip()
                issue_counts[normalized_title] = issue_counts.get(normalized_title, 0) + 1

        # Disagreement = only 1 reviewer found it
        disagreements = [title for title, count in issue_counts.items() if count == 1]
        return disagreements


class ConsensusBuilder:
    """
    Builds consensus from reviewer opinions with severity-based thresholds.

    Different thresholds for different severity levels:
    - Blockers: Unanimous (100%)
    - Major: 2/3 majority (67%)
    - Minor: Simple majority (50%)
    """

    def __init__(
        self,
        blocker_threshold: float = 1.0,
        major_threshold: float = 0.67,
        minor_threshold: float = 0.5,
    ):
        self.blocker_threshold = blocker_threshold
        self.major_threshold = major_threshold
        self.minor_threshold = minor_threshold

    def build_consensus(
        self, opinions: list[ReviewerOpinion], debates: list[DebateRound]
    ) -> ReviewReport:
        """
        Build final review decision from opinions and debate.

        Args:
            opinions: Reviewer opinions
            debates: Debate rounds

        Returns:
            Final review report with decision
        """
        # Collect all issues by severity
        all_issues: list[CodeIssue] = []
        for opinion in opinions:
            all_issues.extend(opinion.issues)

        blocker_issues = [i for i in all_issues if i.severity == Severity.BLOCKER]
        major_issues = [i for i in all_issues if i.severity == Severity.MAJOR]
        minor_issues = [i for i in all_issues if i.severity == Severity.MINOR]
        info_issues = [i for i in all_issues if i.severity == Severity.INFO]

        # Apply consensus thresholds
        consensus_blockers = self._apply_threshold(
            blocker_issues, len(opinions), self.blocker_threshold
        )
        consensus_major = self._apply_threshold(
            major_issues, len(opinions), self.major_threshold
        )
        consensus_minor = self._apply_threshold(
            minor_issues, len(opinions), self.minor_threshold
        )

        # Determine decision
        decision = self._determine_decision(
            consensus_blockers, consensus_major, consensus_minor
        )

        # Calculate confidence
        avg_confidence = (
            sum(o.confidence for o in opinions) / len(opinions) if opinions else 0.0
        )

        # Generate summary
        summary = self._generate_summary(
            decision, consensus_blockers, consensus_major, consensus_minor
        )

        return ReviewReport(
            decision=decision,
            blocker_issues=consensus_blockers,
            major_issues=consensus_major,
            minor_issues=consensus_minor,
            info_issues=info_issues,
            debate_rounds=debates,
            consensus_summary=summary,
            reviewers=[o.reviewer.value for o in opinions],
            confidence_score=avg_confidence,
            timestamp=datetime.now(UTC),
            metadata={
                "total_reviewers": len(opinions),
                "blocker_threshold": self.blocker_threshold,
                "major_threshold": self.major_threshold,
                "minor_threshold": self.minor_threshold,
            },
        )

    def _apply_threshold(
        self, issues: list[CodeIssue], total_reviewers: int, threshold: float
    ) -> list[CodeIssue]:
        """Apply consensus threshold to filter issues."""
        # Group by normalized title
        issue_groups: dict[str, list[CodeIssue]] = {}
        for issue in issues:
            normalized = issue.title.lower().strip()
            if normalized not in issue_groups:
                issue_groups[normalized] = []
            issue_groups[normalized].append(issue)

        # Filter by threshold
        consensus_issues = []
        for group in issue_groups.values():
            agreement_ratio = len(group) / total_reviewers
            if agreement_ratio >= threshold:
                # Take the issue with highest confidence
                best_issue = max(group, key=lambda i: i.confidence)
                consensus_issues.append(best_issue)

        return consensus_issues

    def _determine_decision(
        self,
        blockers: list[CodeIssue],
        major: list[CodeIssue],
        minor: list[CodeIssue],
    ) -> ReviewDecision:
        """Determine final review decision based on issues."""
        if blockers or len(major) > 2:
            return ReviewDecision.REQUEST_CHANGES
        elif major or minor:
            return ReviewDecision.APPROVE_WITH_COMMENTS
        else:
            return ReviewDecision.APPROVE

    def _generate_summary(
        self,
        decision: ReviewDecision,
        blockers: list[CodeIssue],
        major: list[CodeIssue],
        minor: list[CodeIssue],
    ) -> str:
        """Generate consensus summary."""
        parts = []

        if blockers:
            parts.append(
                f"{len(blockers)} blocking issue(s) require immediate attention"
            )
        if major:
            parts.append(f"{len(major)} major issue(s) should be addressed")
        if minor:
            parts.append(f"{len(minor)} minor suggestion(s) for improvement")

        if not parts:
            return "Code review complete. No issues found. Ready to merge! ✅"

        summary = f"Code review complete: {', '.join(parts)}. "
        summary += f"Decision: {decision.value.upper().replace('_', ' ')}."
        return summary


class ReviewCoordinator:
    """
    Coordinates multi-agent code review with debate and consensus.

    Orchestrates the entire review workflow.
    """

    def __init__(
        self,
        reviewers: list[MockReviewerAgent] | None = None,
        debate_rounds: int = 2,
        consensus_thresholds: dict[str, float] | None = None,
        verbose: bool = False,
    ):
        self.reviewers = reviewers or [
            MockReviewerAgent(ReviewerType.SECURITY, "security_1"),
            MockReviewerAgent(ReviewerType.PERFORMANCE, "performance_1"),
            MockReviewerAgent(ReviewerType.MAINTAINABILITY, "maintainability_1"),
        ]
        self.debate_moderator = DebateModerator(max_rounds=debate_rounds)
        self.consensus_builder = ConsensusBuilder(
            **(consensus_thresholds or {})
        )
        self.verbose = verbose

    async def review_code(
        self, code: str, context: dict[str, Any] | None = None
    ) -> ReviewReport:
        """
        Conduct multi-agent code review with debate and consensus.

        Args:
            code: Code to review
            context: Optional context (file_path, diff, etc.)

        Returns:
            Final review report
        """
        if self.verbose:
            print("\n🔍 Starting Code Review")
            print(f"📊 Reviewers: {len(self.reviewers)}")
            print(f"📝 Code length: {len(code)} characters\n")

        # Step 1: Parallel review by all reviewers
        if self.verbose:
            print("👥 Phase 1: Parallel Review...")

        review_tasks = [
            reviewer.process(Message(role="user", content=code))
            for reviewer in self.reviewers
        ]

        results = await asyncio.gather(*review_tasks)

        # Parse opinions from results
        opinions: list[ReviewerOpinion] = []
        for i, result in enumerate(results):
            raw_opinion = json.loads(result.content)
            issues = [
                CodeIssue(
                    severity=Severity(issue["severity"]),
                    reviewer=raw_opinion["reviewer"],
                    title=issue["title"],
                    description=issue["description"],
                    line_number=issue.get("line_number"),
                    suggestion=issue.get("suggestion"),
                    confidence=issue.get("confidence", 0.8),
                )
                for issue in raw_opinion["issues"]
            ]

            opinion = ReviewerOpinion(
                reviewer=self.reviewers[i].reviewer_type,
                issues=issues,
                overall_assessment=raw_opinion["overall_assessment"],
                confidence=raw_opinion["confidence"],
            )
            opinions.append(opinion)

            if self.verbose:
                print(
                    f"  ✓ {opinion.reviewer.value}: Found {len(issues)} issue(s)"
                )

        # Step 2: Debate
        if self.verbose:
            print(f"\n🗣️ Phase 2: Debate ({self.debate_moderator.max_rounds} rounds)...")

        debates = await self.debate_moderator.moderate_debate(opinions)

        if self.verbose:
            for debate in debates:
                print(f"  Round {debate.round_number}:")
                print(f"    Agreement on: {len(debate.areas_of_agreement)} issues")
                print(f"    Disagreement on: {len(debate.areas_of_disagreement)} issues")

        # Step 3: Build consensus
        if self.verbose:
            print("\n🤝 Phase 3: Building Consensus...")

        report = self.consensus_builder.build_consensus(opinions, debates)

        if self.verbose:
            print(f"  ✓ Decision: {report.decision.value.upper().replace('_', ' ')}")
            print(f"  ✓ Blockers: {len(report.blocker_issues)}")
            print(f"  ✓ Major: {len(report.major_issues)}")
            print(f"  ✓ Minor: {len(report.minor_issues)}")
            print(f"  ✓ Confidence: {report.confidence_score:.2f}\n")

        return report


async def main():
    """Run code review example."""
    import sys

    # Sample code to review
    sample_code = '''
def process_user_data(username, password):
    # TODO: Add input validation
    sql = "SELECT * FROM users WHERE username='" + username + "' AND password='" + password + "'"
    cursor.execute(sql)

    results = []
    for user in cursor.fetchall():
        for permission in get_permissions(user.id):
            results.append((user, permission))

    import time
    time.sleep(1)  # Rate limiting

    return results
'''

    # Parse command line args
    code = sample_code
    if len(sys.argv) > 1 and sys.argv[1] == "review":
        if len(sys.argv) > 2:
            file_path = Path(sys.argv[2])
            if file_path.exists():
                code = file_path.read_text()
            else:
                print(f"Error: File not found: {file_path}")
                return
    verbose = "--verbose" in sys.argv

    # Initialize coordinator
    coordinator = ReviewCoordinator(verbose=verbose)

    # Conduct review
    report = await coordinator.review_code(code)

    # Display report
    print("\n" + "=" * 70)
    print(report.to_markdown())
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
