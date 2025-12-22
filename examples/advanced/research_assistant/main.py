"""
Multi-Agent Research Assistant with Consensus and Voting

This example demonstrates advanced multi-agent patterns:
- Consensus Building: Multiple agents agree on facts
- Voting: Democratic decision-making for conflicts
- Reflection: Iterative quality improvement
- Orchestration: Coordinated workflow

Usage:
    python main.py "artificial intelligence trends 2025"
    python main.py "quantum computing" --verbose
    python main.py "climate change" --config custom.yaml
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from agenkit.interfaces import Agent, Message


class ResearchDepth(Enum):
    """Research depth level."""

    SHALLOW = "shallow"  # Quick overview, 1-2 sources
    MODERATE = "moderate"  # Balanced research, 3-5 sources
    COMPREHENSIVE = "comprehensive"  # Deep research, 7-10 sources


@dataclass
class Finding:
    """A research finding from an agent."""

    claim: str
    source: str
    confidence: float  # 0.0-1.0
    agent_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ConsensusFact:
    """A fact verified by consensus."""

    claim: str
    sources: list[str]
    agreement_score: float  # Percentage of agents agreeing
    confidence: float  # Average confidence
    supporting_agents: list[str]


@dataclass
class ResearchReport:
    """Final research report."""

    topic: str
    summary: str
    facts: list[ConsensusFact]
    citations: list[str]
    confidence_score: float
    timestamp: datetime
    metadata: dict[str, Any]


class MockResearchAgent(Agent):
    """
    Mock research agent for demonstration.

    In production, this would:
    - Search the web using APIs (Serper, Brave, etc.)
    - Extract facts from web pages
    - Cite sources properly
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._name = f"researcher_{agent_id}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["search", "extract_facts", "cite_sources"]

    async def process(self, message: Message) -> Message:
        """
        Simulate research process.

        In production, would:
        1. Parse research topic from message
        2. Execute web searches
        3. Extract facts from results
        4. Return structured findings
        """
        topic = message.content

        # Simulate research findings (in production, would search web)
        findings = self._simulate_research(topic)

        response_content = json.dumps(findings, indent=2)

        return Message(
            role="assistant",
            content=response_content,
            metadata={
                "agent_id": self.agent_id,
                "findings_count": len(findings),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    def _simulate_research(self, topic: str) -> list[dict[str, Any]]:
        """
        Simulate research findings.

        In production, would execute real searches and extract facts.
        """
        # Simulate different perspectives from different agents
        perspectives = {
            "agent_1": [
                {
                    "claim": f"{topic} is rapidly evolving with new developments",
                    "source": "https://example.com/article1",
                    "confidence": 0.85,
                },
                {
                    "claim": f"Recent advances in {topic} show promising results",
                    "source": "https://example.com/article2",
                    "confidence": 0.90,
                },
            ],
            "agent_2": [
                {
                    "claim": f"{topic} is rapidly evolving with new developments",
                    "source": "https://example.com/article3",
                    "confidence": 0.88,
                },
                {
                    "claim": f"Experts predict significant growth in {topic} by 2025",
                    "source": "https://example.com/article4",
                    "confidence": 0.75,
                },
            ],
            "agent_3": [
                {
                    "claim": f"{topic} is rapidly evolving with new developments",
                    "source": "https://example.com/article5",
                    "confidence": 0.92,
                },
                {
                    "claim": f"Investment in {topic} reached record levels in 2024",
                    "source": "https://example.com/article6",
                    "confidence": 0.80,
                },
            ],
        }

        return perspectives.get(self.agent_id, [])


class ConsensusBuilder:
    """
    Builds consensus from multiple agent findings.

    Uses voting to determine which facts meet consensus threshold.
    """

    def __init__(self, threshold: float = 0.67):
        """
        Initialize consensus builder.

        Args:
            threshold: Minimum agreement ratio (0.0-1.0) to accept a fact
                      0.67 = 2/3 majority (67% agreement)
        """
        self.threshold = threshold

    def build_consensus(self, findings_list: list[list[Finding]]) -> list[ConsensusFact]:
        """
        Build consensus from multiple agents' findings.

        Args:
            findings_list: List of findings from each agent

        Returns:
            List of facts that meet consensus threshold
        """
        # Group findings by claim (normalize for comparison)
        claim_groups: dict[str, list[Finding]] = {}

        for findings in findings_list:
            for finding in findings:
                normalized_claim = self._normalize_claim(finding.claim)
                if normalized_claim not in claim_groups:
                    claim_groups[normalized_claim] = []
                claim_groups[normalized_claim].append(finding)

        # Build consensus facts
        consensus_facts = []
        total_agents = len(findings_list)

        for normalized_claim, findings in claim_groups.items():
            agreement_score = len(findings) / total_agents

            # Check if meets consensus threshold
            if agreement_score >= self.threshold:
                consensus_fact = ConsensusFact(
                    claim=findings[0].claim,  # Use original claim text
                    sources=[f.source for f in findings],
                    agreement_score=agreement_score,
                    confidence=sum(f.confidence for f in findings) / len(findings),
                    supporting_agents=[f.agent_id for f in findings],
                )
                consensus_facts.append(consensus_fact)

        return consensus_facts

    def _normalize_claim(self, claim: str) -> str:
        """Normalize claim for comparison (lowercase, remove punctuation)."""
        return claim.lower().strip().rstrip(".")


class VotingResolver:
    """
    Resolves conflicts using voting when consensus cannot be reached.

    Implements majority voting, plurality voting, and ranked-choice voting.
    """

    def majority_vote(self, votes: list[bool]) -> bool:
        """Simple majority vote (>50%)."""
        return sum(votes) > len(votes) / 2

    def plurality_vote(self, options: list[str], votes: list[str]) -> str:
        """Return option with most votes."""
        vote_counts = {option: votes.count(option) for option in options}
        return max(vote_counts, key=vote_counts.get)  # type: ignore

    def confidence_weighted_vote(self, votes: list[tuple[bool, float]]) -> tuple[bool, float]:
        """
        Weighted voting based on agent confidence.

        Args:
            votes: List of (vote, confidence) tuples

        Returns:
            (winning_vote, confidence)
        """
        weighted_sum = sum((1.0 if vote else 0.0) * conf for vote, conf in votes)
        total_weight = sum(conf for _, conf in votes)

        if total_weight == 0:
            return (False, 0.0)

        weighted_avg = weighted_sum / total_weight
        return (weighted_avg > 0.5, weighted_avg)


class ResearchCoordinator:
    """
    Coordinates multi-agent research with consensus building.

    Demonstrates orchestration, consensus, and voting patterns.
    """

    def __init__(
        self,
        num_researchers: int = 3,
        consensus_threshold: float = 0.67,
        verbose: bool = False,
    ):
        self.num_researchers = num_researchers
        self.consensus_threshold = consensus_threshold
        self.verbose = verbose
        self.consensus_builder = ConsensusBuilder(threshold=consensus_threshold)
        self.voting_resolver = VotingResolver()

    async def research(
        self, topic: str, depth: ResearchDepth = ResearchDepth.MODERATE
    ) -> ResearchReport:
        """
        Conduct multi-agent research with consensus building.

        Args:
            topic: Research topic
            depth: Research depth level

        Returns:
            Research report with consensus facts
        """
        if self.verbose:
            print(f"\n🔬 Starting research on: {topic}")
            print(f"📊 Using {self.num_researchers} researchers")
            print(f"✅ Consensus threshold: {self.consensus_threshold * 100}%\n")

        # Step 1: Parallel research by multiple agents
        if self.verbose:
            print("📚 Phase 1: Parallel Research...")

        researchers = [
            MockResearchAgent(agent_id=f"agent_{i + 1}") for i in range(self.num_researchers)
        ]

        research_tasks = [
            researcher.process(Message(role="user", content=topic)) for researcher in researchers
        ]

        results = await asyncio.gather(*research_tasks)

        # Parse findings from each agent
        findings_list = []
        for i, result in enumerate(results):
            raw_findings = json.loads(result.content)
            findings = [
                Finding(
                    claim=f["claim"],
                    source=f["source"],
                    confidence=f["confidence"],
                    agent_id=f"agent_{i + 1}",
                )
                for f in raw_findings
            ]
            findings_list.append(findings)

            if self.verbose:
                print(f"  ✓ Agent {i + 1}: Found {len(findings)} facts")

        # Step 2: Build consensus
        if self.verbose:
            print(f"\n🤝 Phase 2: Building Consensus (threshold: {self.consensus_threshold})...")

        consensus_facts = self.consensus_builder.build_consensus(findings_list)

        if self.verbose:
            print(f"  ✓ Consensus reached on {len(consensus_facts)} facts")
            for i, fact in enumerate(consensus_facts, 1):
                print(
                    f"    {i}. {fact.claim[:60]}... ({fact.agreement_score * 100:.0f}% agreement)"
                )

        # Step 3: Generate report
        if self.verbose:
            print("\n📝 Phase 3: Generating Report...")

        report = self._generate_report(topic, consensus_facts)

        if self.verbose:
            print(f"  ✓ Report generated with {len(report.facts)} facts")
            print(f"  ✓ Overall confidence: {report.confidence_score:.2f}\n")

        return report

    def _generate_report(self, topic: str, consensus_facts: list[ConsensusFact]) -> ResearchReport:
        """Generate final research report."""
        # Collect all unique citations
        all_citations = set()
        for fact in consensus_facts:
            all_citations.update(fact.sources)

        # Calculate overall confidence
        if consensus_facts:
            avg_confidence = sum(f.confidence for f in consensus_facts) / len(consensus_facts)
        else:
            avg_confidence = 0.0

        # Generate summary
        summary = self._generate_summary(topic, consensus_facts)

        return ResearchReport(
            topic=topic,
            summary=summary,
            facts=consensus_facts,
            citations=sorted(all_citations),
            confidence_score=avg_confidence,
            timestamp=datetime.now(UTC),
            metadata={
                "num_researchers": self.num_researchers,
                "consensus_threshold": self.consensus_threshold,
                "facts_found": len(consensus_facts),
            },
        )

    def _generate_summary(self, topic: str, facts: list[ConsensusFact]) -> str:
        """Generate report summary."""
        if not facts:
            return f"Insufficient consensus on {topic}. Try lowering consensus threshold."

        return (
            f"Research on '{topic}' revealed {len(facts)} key findings "
            f"verified by multiple sources with average confidence of "
            f"{sum(f.confidence for f in facts) / len(facts):.2f}."
        )


async def main():
    """Run research assistant example."""
    import sys

    # Parse command line args
    topic = sys.argv[1] if len(sys.argv) > 1 else "artificial intelligence trends 2025"
    verbose = "--verbose" in sys.argv

    # Initialize coordinator
    coordinator = ResearchCoordinator(num_researchers=3, consensus_threshold=0.67, verbose=verbose)

    # Conduct research
    report = await coordinator.research(topic, depth=ResearchDepth.MODERATE)

    # Display report
    print("\n" + "=" * 70)
    print(f"RESEARCH REPORT: {report.topic}")
    print("=" * 70)
    print(f"\n📝 Summary:\n{report.summary}\n")
    print(f"✅ Consensus Facts ({len(report.facts)}):")
    for i, fact in enumerate(report.facts, 1):
        print(f"\n{i}. {fact.claim}")
        print(
            f"   Agreement: {fact.agreement_score * 100:.0f}% | Confidence: {fact.confidence:.2f}"
        )
        print(f"   Sources ({len(fact.sources)}): {', '.join(fact.sources[:2])}")

    print(f"\n📚 Citations ({len(report.citations)}):")
    for i, citation in enumerate(report.citations, 1):
        print(f"  [{i}] {citation}")

    print("\n📊 Metadata:")
    print(f"  Researchers: {report.metadata['num_researchers']}")
    print(f"  Consensus Threshold: {report.metadata['consensus_threshold'] * 100}%")
    print(f"  Overall Confidence: {report.confidence_score:.2f}")
    print(f"  Timestamp: {report.timestamp.isoformat()}")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
