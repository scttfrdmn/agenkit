"""Synthesis agent - combines all review results into final report."""

from typing import List, Dict
from datetime import datetime
from agenkit import Agent, Message
from agents.review_types import ReviewResult, CodeIssue, IssueSeverity


class SynthesisAgent(Agent):
    """Synthesizes all review results into a comprehensive final report."""

    @property
    def name(self) -> str:
        return "SynthesisAgent"

    async def process(self, message: Message) -> Message:
        """Synthesize review results from all agents."""
        review_results = message.metadata.get("review_results", [])

        if not review_results:
            return Message(
                role="assistant",
                content="No review results to synthesize",
                metadata={"error": "No review_results in metadata"},
            )

        start_time = datetime.now()
        report = self._synthesize_report(review_results)
        execution_time = (datetime.now() - start_time).total_seconds()

        return Message(
            role="assistant",
            content=report,
            metadata={
                "execution_time": execution_time,
                "total_issues": sum(len(r.issues) for r in review_results),
            },
        )

    def _synthesize_report(self, results: List[ReviewResult]) -> str:
        """Create comprehensive review report."""
        all_issues = []
        for result in results:
            all_issues.extend(result.issues)

        # Group by severity
        by_severity: Dict[IssueSeverity, List[CodeIssue]] = {
            IssueSeverity.CRITICAL: [],
            IssueSeverity.HIGH: [],
            IssueSeverity.MEDIUM: [],
            IssueSeverity.LOW: [],
            IssueSeverity.INFO: [],
        }

        for issue in all_issues:
            by_severity[issue.severity].append(issue)

        # Calculate overall metrics
        total_issues = len(all_issues)
        critical_count = len(by_severity[IssueSeverity.CRITICAL])
        high_count = len(by_severity[IssueSeverity.HIGH])
        medium_count = len(by_severity[IssueSeverity.MEDIUM])
        low_count = len(by_severity[IssueSeverity.LOW])

        avg_score = sum(r.overall_score for r in results) / len(results) if results else 0.0
        all_passed = all(r.passed for r in results)

        # Build report
        lines = []
        lines.append("=" * 70)
        lines.append("CODE REVIEW REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Overall verdict
        verdict = "✓ PASSED" if all_passed else "✗ FAILED"
        lines.append(f"Overall Verdict: {verdict}")
        lines.append(f"Average Score: {avg_score:.1f}/10.0")
        lines.append(f"Total Issues: {total_issues}")
        lines.append("")

        # Summary by severity
        lines.append("Issues by Severity:")
        lines.append(f"  Critical: {critical_count}")
        lines.append(f"  High:     {high_count}")
        lines.append(f"  Medium:   {medium_count}")
        lines.append(f"  Low:      {low_count}")
        lines.append("")

        # Agent results
        lines.append("Agent Results:")
        for result in results:
            status = "✓" if result.passed else "✗"
            lines.append(f"  {status} {result.agent_name}: {result.overall_score:.1f}/10 - {len(result.issues)} issues")
        lines.append("")

        # Critical issues first
        if critical_count > 0:
            lines.append("=" * 70)
            lines.append("CRITICAL ISSUES (Must Fix)")
            lines.append("=" * 70)
            for i, issue in enumerate(by_severity[IssueSeverity.CRITICAL], 1):
                lines.append(f"\n{i}. [{issue.category.value.upper()}] {issue.message}")
                if issue.line_number:
                    lines.append(f"   Location: Line {issue.line_number}")
                if issue.code_snippet:
                    lines.append(f"   Code: {issue.code_snippet}")
                if issue.suggestion:
                    lines.append(f"   Fix: {issue.suggestion}")
            lines.append("")

        # High severity issues
        if high_count > 0:
            lines.append("=" * 70)
            lines.append("HIGH SEVERITY ISSUES")
            lines.append("=" * 70)
            for i, issue in enumerate(by_severity[IssueSeverity.HIGH][:5], 1):  # Top 5
                lines.append(f"\n{i}. [{issue.category.value}] {issue.message}")
                if issue.line_number:
                    lines.append(f"   Line {issue.line_number}")
                if issue.suggestion:
                    lines.append(f"   Suggestion: {issue.suggestion}")
            if high_count > 5:
                lines.append(f"\n... and {high_count - 5} more high severity issues")
            lines.append("")

        # Summary
        lines.append("=" * 70)
        lines.append("RECOMMENDATION")
        lines.append("=" * 70)
        if critical_count > 0:
            lines.append(f"❌ Code review FAILED with {critical_count} critical issues.")
            lines.append("   These must be fixed before merging.")
        elif high_count > 0:
            lines.append(f"⚠️  Code review passed with warnings: {high_count} high severity issues.")
            lines.append("   Recommend addressing before merging.")
        elif medium_count > 5:
            lines.append(f"⚠️  Code review passed but has {medium_count} medium issues.")
            lines.append("   Consider addressing in follow-up.")
        else:
            lines.append("✅ Code review PASSED - good to merge!")
        lines.append("=" * 70)

        return "\n".join(lines)
