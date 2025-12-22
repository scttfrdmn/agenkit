"""
Supervisor Pattern Usage Example.

Demonstrates the Supervisor pattern for hierarchical coordination with
task decomposition and delegation.

Use cases:
- Complex task decomposition
- Hierarchical agent coordination
- Dynamic task planning
- Multi-step workflows

This example shows:
- Breaking down complex tasks
- Delegating to specialized agents
- Collecting and synthesizing results
- Dynamic planning based on input
"""

import asyncio

from agenkit.core import Agent, Message
from agenkit.patterns import SimplePlanner, Subtask, SupervisorAgent


class ResearchAgent(Agent):
    """Conducts research on topics."""

    def name(self) -> str:
        return "ResearchAgent"

    def capabilities(self) -> list[str]:
        return ["research", "information-gathering"]

    async def process(self, message: Message) -> Message:
        """Research a topic."""
        print(f"   🔍 Researching: {message.content}")
        await asyncio.sleep(0.1)

        topic = message.content.lower()
        info = f"Research findings on '{topic}':\n"
        info += "- Key concepts identified\n"
        info += "- 5 relevant sources found\n"
        info += "- Summary: [detailed information]\n"

        result = Message(role="agent", content=info)
        result.metadata["subtask_type"] = "research"
        return result


class AnalysisAgent(Agent):
    """Analyzes data and findings."""

    def name(self) -> str:
        return "AnalysisAgent"

    def capabilities(self) -> list[str]:
        return ["analysis", "evaluation"]

    async def process(self, message: Message) -> Message:
        """Analyze findings."""
        print("   📊 Analyzing findings...")
        await asyncio.sleep(0.12)

        analysis = "Analysis Results:\n"
        analysis += "- Patterns identified: 3 major trends\n"
        analysis += "- Confidence level: High\n"
        analysis += "- Recommendations: [detailed analysis]\n"

        result = Message(role="agent", content=analysis)
        result.metadata["subtask_type"] = "analysis"
        return result


class WriterAgent(Agent):
    """Writes reports and summaries."""

    def name(self) -> str:
        return "WriterAgent"

    def capabilities(self) -> list[str]:
        return ["writing", "summarization"]

    async def process(self, message: Message) -> Message:
        """Write a report."""
        print("   ✍️  Writing report...")
        await asyncio.sleep(0.15)

        report = "Executive Summary Report\n"
        report += "=" * 40 + "\n\n"
        report += "Based on comprehensive research and analysis:\n\n"
        report += "1. Key Findings\n"
        report += "   - Finding A: [detailed point]\n"
        report += "   - Finding B: [detailed point]\n\n"
        report += "2. Recommendations\n"
        report += "   - Recommendation 1: [action item]\n"
        report += "   - Recommendation 2: [action item]\n\n"
        report += "3. Conclusion\n"
        report += "   [Summary conclusion]\n"

        result = Message(role="agent", content=report)
        result.metadata["subtask_type"] = "writing"
        return result


class CustomPlanner(SimplePlanner):
    """Custom planner for report generation tasks."""

    def plan(self, message: Message) -> list[Subtask]:
        """Create task plan based on request."""
        # Extract task requirements
        content = message.content.lower()

        subtasks = []

        # Always start with research
        if "research" in content or "report" in content:
            subtasks.append(
                Subtask(
                    description="Research the topic",
                    agent_capability="research",
                )
            )

        # Add analysis if needed
        if "analyze" in content or "analysis" in content or "report" in content:
            subtasks.append(
                Subtask(
                    description="Analyze the findings",
                    agent_capability="analysis",
                )
            )

        # Add writing if needed
        if "write" in content or "report" in content or "summary" in content:
            subtasks.append(
                Subtask(
                    description="Write the final report",
                    agent_capability="writing",
                )
            )

        return subtasks


async def basic_supervision():
    """Demonstrate basic supervised task decomposition."""
    print("=" * 60)
    print("Example 1: Basic Report Generation")
    print("=" * 60)

    # Create supervisor with specialized agents
    supervisor = SupervisorAgent(
        planner=CustomPlanner(),
        workers=[
            ResearchAgent(),
            AnalysisAgent(),
            WriterAgent(),
        ],
    )

    message = Message(
        role="user",
        content="Create a report on AI agent frameworks",
    )

    print(f"\n📥 Task: {message.content}\n")
    print("Supervisor decomposing task...")

    result = await supervisor.process(message)

    print(f"\n📤 Final Result:\n{result.content}")
    print("\nTask Execution:")
    print(f"   Subtasks completed: {result.metadata.get('subtasks_completed', 0)}")
    print(f"   Workers used: {len(result.metadata.get('worker_results', []))}")


async def partial_task():
    """Demonstrate handling of partial task requirements."""
    print("\n\n" + "=" * 60)
    print("Example 2: Research-Only Task")
    print("=" * 60)

    supervisor = SupervisorAgent(
        planner=CustomPlanner(),
        workers=[
            ResearchAgent(),
            AnalysisAgent(),
            WriterAgent(),
        ],
    )

    message = Message(
        role="user",
        content="Research machine learning frameworks",
    )

    print(f"\n📥 Task: {message.content}\n")
    print("Supervisor planning subtasks...")

    result = await supervisor.process(message)

    print(f"\n📤 Result:\n{result.content}")
    print("\nTask Execution:")
    print(f"   Subtasks planned: {result.metadata.get('subtasks_planned', 0)}")
    print(f"   Subtasks completed: {result.metadata.get('subtasks_completed', 0)}")


async def error_handling():
    """Demonstrate error handling in supervised execution."""
    print("\n\n" + "=" * 60)
    print("Example 3: Error Handling")
    print("=" * 60)

    class FailingAgent(Agent):
        """An agent that fails to demonstrate error handling."""

        def name(self) -> str:
            return "FailingAgent"

        def capabilities(self) -> list[str]:
            return ["analysis"]  # Will be matched by planner

        async def process(self, message: Message) -> Message:
            raise RuntimeError("Simulated worker failure")

    supervisor = SupervisorAgent(
        planner=CustomPlanner(),
        workers=[
            ResearchAgent(),
            FailingAgent(),  # Will fail on analysis
            WriterAgent(),
        ],
    )

    message = Message(
        role="user",
        content="Create a report on distributed systems",
    )

    print(f"\n📥 Task: {message.content}\n")
    print("Processing with failing worker...")

    try:
        result = await supervisor.process(message)
        print(f"Result: {result.content}")
    except Exception as e:
        print(f"✓ Supervisor caught worker error (expected): {e}")


async def metadata_flow():
    """Demonstrate metadata flow through supervision."""
    print("\n\n" + "=" * 60)
    print("Example 4: Metadata and Context Flow")
    print("=" * 60)

    supervisor = SupervisorAgent(
        planner=CustomPlanner(),
        workers=[
            ResearchAgent(),
            AnalysisAgent(),
            WriterAgent(),
        ],
    )

    message = Message(
        role="user",
        content="Write a comprehensive report on agent patterns",
    )
    message.metadata["priority"] = "high"
    message.metadata["deadline"] = "2024-02-01"

    print(f"\n📥 Task: {message.content}")
    print(f"   Priority: {message.metadata['priority']}")
    print(f"   Deadline: {message.metadata['deadline']}\n")

    result = await supervisor.process(message)

    print(f"\n📤 Result preview:\n{result.content[:200]}...")
    print("\nExecution Details:")
    if "worker_results" in result.metadata:
        for i, worker_result in enumerate(result.metadata["worker_results"], 1):
            print(f"   Step {i}: {worker_result.get('agent')} - {worker_result.get('subtask')}")


async def main():
    """Run all examples."""
    print("\n👔 Supervisor Pattern Usage Examples\n")

    await basic_supervision()
    await partial_task()
    await error_handling()
    await metadata_flow()

    print("\n✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
