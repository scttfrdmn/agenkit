"""Review orchestrator - coordinates parallel agent execution."""

import asyncio
from typing import List
from datetime import datetime
from agenkit import Message
from agents import (
    StyleAgent,
    SecurityAgent,
    PerformanceAgent,
    CorrectnessAgent,
    SynthesisAgent,
    ReviewResult,
    CodeSubmission,
)


class ReviewOrchestrator:
    """
    Orchestrates parallel code review by multiple specialized agents.

    Runs review agents in parallel, then synthesizes results.
    """

    def __init__(self, verbose: bool = True):
        """Initialize orchestrator with all review agents."""
        self.verbose = verbose

        # Initialize review agents
        self.style_agent = StyleAgent()
        self.security_agent = SecurityAgent()
        self.performance_agent = PerformanceAgent()
        self.correctness_agent = CorrectnessAgent()
        self.synthesis_agent = SynthesisAgent()

        self.review_agents = [
            self.style_agent,
            self.security_agent,
            self.performance_agent,
            self.correctness_agent,
        ]

        if self.verbose:
            print(f"✓ Review orchestrator initialized with {len(self.review_agents)} agents")

    async def review_code(self, submission: CodeSubmission) -> str:
        """
        Execute parallel code review.

        Args:
            submission: Code to review

        Returns:
            Final review report as string
        """
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"CODE REVIEW: {submission.file_path or 'Inline Code'}")
            print(f"{'='*70}")
            print(f"Lines: {submission.get_line_count()}, Language: {submission.language or 'unknown'}")
            print(f"\nExecuting {len(self.review_agents)} review agents in parallel...")

        start_time = datetime.now()

        # Run all review agents in parallel
        review_tasks = [
            agent.process(
                Message(
                    role="user",
                    content=submission.content,
                    metadata={"code_submission": submission},
                )
            )
            for agent in self.review_agents
        ]

        review_messages = await asyncio.gather(*review_tasks)
        parallel_time = (datetime.now() - start_time).total_seconds()

        if self.verbose:
            print(f"✓ Parallel review complete in {parallel_time:.2f}s")

        # Extract review results
        review_results: List[ReviewResult] = []
        for msg in review_messages:
            if "review_result" in msg.metadata:
                result = msg.metadata["review_result"]
                review_results.append(result)

                if self.verbose:
                    status = "✓" if result.passed else "✗"
                    print(f"  {status} {result.agent_name}: {result.overall_score:.1f}/10 - {len(result.issues)} issues ({result.execution_time:.3f}s)")

        # Synthesize results
        if self.verbose:
            print(f"\nSynthesizing final report...")

        synthesis_msg = await self.synthesis_agent.process(
            Message(
                role="assistant",
                content="",
                metadata={"review_results": review_results},
            )
        )

        total_time = (datetime.now() - start_time).total_seconds()

        if self.verbose:
            print(f"✓ Review complete in {total_time:.2f}s total")

        return synthesis_msg.content
