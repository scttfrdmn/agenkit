"""
Multi-Agent Collaboration Example

Demonstrates how multiple agents can work together through:
- Orchestration: Coordinating multiple specialized agents
- Consensus: Combining perspectives from multiple agents
- Task delegation: Routing work to appropriate specialists

The Multi-Agent pattern is useful for:
- Complex tasks requiring diverse expertise
- Problems benefiting from multiple perspectives
- Parallelizable workflows
- Systems with specialized components

This example uses mock implementations for demonstration.
"""

import asyncio
from typing import List

from agenkit import Agent, Message
from agenkit.patterns import (
    MultiAgentOrchestrator,
    ConsensusAgent,
    AgentTask,
)


# ============================================================================
# Mock Specialized Agents
# ============================================================================


class ResearchAgent(Agent):
    """Agent specialized in research and information gathering."""

    @property
    def name(self) -> str:
        return "ResearchAgent"

    async def process(self, message: Message) -> Message:
        """Process research requests."""
        content = message.content.lower()

        if "market" in content:
            result = "Market research shows strong growth in AI sector (15% YoY)."
        elif "competitor" in content:
            result = "Main competitors: CompanyA (35%), CompanyB (28%), Others (37%)."
        elif "customer" in content:
            result = "Customer survey: 85% satisfaction, top request is mobile app."
        else:
            result = "Research findings: Topic shows significant interest and potential."

        return Message(role="assistant", content=result)


class AnalysisAgent(Agent):
    """Agent specialized in data analysis."""

    @property
    def name(self) -> str:
        return "AnalysisAgent"

    async def process(self, message: Message) -> Message:
        """Process analysis requests."""
        content = message.content.lower()

        if "market" in content:
            result = "Analysis: Market opportunity estimated at $500M, growing segment."
        elif "competitor" in content:
            result = "Analysis: We have competitive advantage in pricing and features."
        elif "customer" in content:
            result = "Analysis: Customer retention is strong (92%), upsell opportunity exists."
        else:
            result = "Analysis: Data indicates positive trend with manageable risks."

        return Message(role="assistant", content=result)


class WritingAgent(Agent):
    """Agent specialized in content creation."""

    @property
    def name(self) -> str:
        return "WritingAgent"

    async def process(self, message: Message) -> Message:
        """Process writing requests."""
        content = message.content.lower()

        if "market" in content:
            result = "Market Report: The AI market presents compelling opportunities..."
        elif "competitor" in content:
            result = "Competitive Analysis: Our positioning offers clear advantages..."
        elif "customer" in content:
            result = "Customer Insights: Feedback reveals strong satisfaction and loyalty..."
        else:
            result = "Report: Comprehensive analysis shows favorable outlook..."

        return Message(role="assistant", content=result)


class CodeReviewAgent(Agent):
    """Agent specialized in code review."""

    @property
    def name(self) -> str:
        return "CodeReviewAgent"

    async def process(self, message: Message) -> Message:
        """Review code."""
        return Message(
            role="assistant",
            content="Code Review: Structure is sound, suggest adding unit tests.",
        )


class SecurityReviewAgent(Agent):
    """Agent specialized in security review."""

    @property
    def name(self) -> str:
        return "SecurityReviewAgent"

    async def process(self, message: Message) -> Message:
        """Review security."""
        return Message(
            role="assistant",
            content="Security Review: Input validation needed, use parameterized queries.",
        )


class PerformanceReviewAgent(Agent):
    """Agent specialized in performance review."""

    @property
    def name(self) -> str:
        return "PerformanceReviewAgent"

    async def process(self, message: Message) -> Message:
        """Review performance."""
        return Message(
            role="assistant",
            content="Performance Review: Consider caching for database queries.",
        )


# ============================================================================
# Example Functions
# ============================================================================


async def basic_orchestration_example():
    """Demonstrate basic multi-agent orchestration."""
    print("=" * 60)
    print("Example 1: Basic Orchestration")
    print("=" * 60)

    # Create specialized agents
    orchestrator = MultiAgentOrchestrator(strategy="sequential")
    orchestrator.register_agent("researcher", ResearchAgent())
    orchestrator.register_agent("analyst", AnalysisAgent())
    orchestrator.register_agent("writer", WritingAgent())

    print("\nTask: Analyze the AI market")
    print(f"Registered agents: {orchestrator.list_agents()}")

    result = await orchestrator.process(
        Message(role="user", content="Analyze the AI market")
    )

    print(f"\nCombined result:\n{result.content}")

    # Show task tracking
    print("\nTask execution details:")
    for task in orchestrator.get_tasks():
        status_icon = "✓" if task.status == "completed" else "✗"
        print(f"  {status_icon} {task.agent_name}: {task.status}")


async def consensus_example():
    """Demonstrate consensus-based decision making."""
    print("\n" + "=" * 60)
    print("Example 2: Consensus Decision Making")
    print("=" * 60)

    # Create consensus agent with multiple reviewers
    consensus = ConsensusAgent(voting_strategy="majority")
    consensus.add_agent(CodeReviewAgent())
    consensus.add_agent(SecurityReviewAgent())
    consensus.add_agent(PerformanceReviewAgent())

    print("\nTask: Review code changes")
    print(f"Number of agents: {len(consensus.agents)}")

    result = await consensus.process(
        Message(role="user", content="Review this code change")
    )

    print(f"\n{result.content}")


async def specialized_agents_example():
    """Demonstrate routing to specialized agents."""
    print("\n" + "=" * 60)
    print("Example 3: Specialized Agent Routing")
    print("=" * 60)

    # Create different orchestrators for different tasks
    research_team = MultiAgentOrchestrator()
    research_team.register_agent("researcher", ResearchAgent())
    research_team.register_agent("analyst", AnalysisAgent())

    review_team = MultiAgentOrchestrator()
    review_team.register_agent("code_review", CodeReviewAgent())
    review_team.register_agent("security", SecurityReviewAgent())

    # Run different tasks
    print("\nRunning market research...")
    research_result = await research_team.process(
        Message(role="user", content="Research competitor landscape")
    )
    print(f"\nResearch team result:\n{research_result.content}")

    print("\n" + "-" * 60)
    print("\nRunning code review...")
    review_result = await review_team.process(
        Message(role="user", content="Review this pull request")
    )
    print(f"\nReview team result:\n{review_result.content}")


async def agent_management_example():
    """Demonstrate dynamic agent management."""
    print("\n" + "=" * 60)
    print("Example 4: Dynamic Agent Management")
    print("=" * 60)

    orchestrator = MultiAgentOrchestrator()

    # Add agents dynamically
    print("\nAdding agents...")
    orchestrator.register_agent("researcher", ResearchAgent())
    print(f"Agents: {orchestrator.list_agents()}")

    orchestrator.register_agent("analyst", AnalysisAgent())
    print(f"Agents: {orchestrator.list_agents()}")

    # Process a task
    print("\nProcessing task...")
    result = await orchestrator.process(
        Message(role="user", content="Analyze customer feedback")
    )
    print(f"\nResult:\n{result.content}")

    # Remove an agent
    print("\n" + "-" * 60)
    print("\nRemoving analyst...")
    orchestrator.unregister_agent("analyst")
    print(f"Agents: {orchestrator.list_agents()}")

    # Process again with fewer agents
    print("\nProcessing task again...")
    result = await orchestrator.process(
        Message(role="user", content="Analyze customer feedback")
    )
    print(f"\nResult:\n{result.content}")


async def task_tracking_example():
    """Demonstrate task tracking and monitoring."""
    print("\n" + "=" * 60)
    print("Example 5: Task Tracking")
    print("=" * 60)

    orchestrator = MultiAgentOrchestrator()
    orchestrator.register_agent("researcher", ResearchAgent())
    orchestrator.register_agent("analyst", AnalysisAgent())
    orchestrator.register_agent("writer", WritingAgent())

    # Execute multiple tasks
    tasks = [
        "Research the market",
        "Analyze competitors",
        "Write a summary",
    ]

    print("\nExecuting multiple tasks...")
    for task_desc in tasks:
        print(f"\n→ Task: {task_desc}")
        await orchestrator.process(Message(role="user", content=task_desc))

    # Show all executed tasks
    print("\n" + "-" * 60)
    print("\nAll executed tasks:")
    all_tasks = orchestrator.get_tasks()
    print(f"Total tasks executed: {len(all_tasks)}")

    # Group by agent
    print("\nTasks by agent:")
    from collections import defaultdict

    tasks_by_agent = defaultdict(list)
    for task in all_tasks:
        tasks_by_agent[task.agent_name].append(task)

    for agent_name, agent_tasks in tasks_by_agent.items():
        print(f"\n  {agent_name}: {len(agent_tasks)} tasks")
        for task in agent_tasks:
            status_icon = {"completed": "✓", "failed": "✗", "pending": "○"}.get(
                task.status, "?"
            )
            print(f"    {status_icon} {task.description}")


async def main():
    """Run all examples."""
    await basic_orchestration_example()
    await consensus_example()
    await specialized_agents_example()
    await agent_management_example()
    await task_tracking_example()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. MultiAgentOrchestrator coordinates multiple specialized agents")
    print("2. ConsensusAgent combines perspectives from multiple agents")
    print("3. Agents can be dynamically added/removed")
    print("4. Task tracking provides visibility into execution")
    print("5. Different teams can handle different types of work")
    print("\nNext Steps:")
    print("- Replace mock agents with real implementations")
    print("- Implement parallel execution for independent tasks")
    print("- Add sophisticated consensus mechanisms (voting, weighting)")
    print("- Integrate with LLMs for intelligent routing")
    print("- Add error handling and retry logic")


if __name__ == "__main__":
    asyncio.run(main())
