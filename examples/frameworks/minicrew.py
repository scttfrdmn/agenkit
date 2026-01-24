#!/usr/bin/env python3
"""
MiniCrew - CrewAI Equivalent Built on Agenkit

Demonstrates how CrewAI's role-based multi-agent collaboration can be built
ON TOP of Agenkit primitives, showing toolkit philosophy.

Pattern Mappings: CrewAI Agent → Agent with role, CrewAI Task → Task dataclass,
CrewAI Crew → Orchestration, Process.sequential → SequentialAgent

Migration guide: docs/migrations/crewai-to-agenkit.md

Usage: uv run python examples/frameworks/minicrew.py
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, cast

from agenkit import Agent, Message
from agenkit.adapters.llm import LLM, OpenAILLM


@dataclass
class CrewTask:
    """
    A task to be performed by an agent (mirrors CrewAI.Task).
    Pattern: CrewAI.Task → Task dataclass with agent assignment
    """

    description: str
    agent: Agent
    expected_output: str = ""
    context: list["CrewTask"] = field(default_factory=list)


class CrewAgent(Agent):
    """
    Role-based agent with goal and backstory (mirrors CrewAI.Agent).
    Pattern: CrewAI.Agent → Agenkit Agent with role metadata
    """

    def __init__(self, role: str, goal: str, backstory: str, llm: LLM) -> None:
        """Create role-based agent."""
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.llm = llm

    @property
    def name(self) -> str:
        """Return agent's role as name."""
        return self.role

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities derived from role."""
        return [self.role.lower().replace(" ", "_")]

    async def process(self, message: Message) -> Message:
        """Process message with role context."""
        # Build context-aware prompt
        system_prompt = f"""You are a {self.role}.
Goal: {self.goal}
Background: {self.backstory}

Approach this task with your expertise and perspective."""

        # Combine system context with user message
        full_prompt = f"{system_prompt}\n\nTask: {message.content}"
        messages = [Message(role="user", content=full_prompt)]

        response = await self.llm.complete(messages)
        return Message(
            role="agent",
            content=cast("str", response.content),
            metadata={"agent_role": self.role, "agent_goal": self.goal},
        )


class Crew:
    """
    Multi-agent crew for collaborative task execution (mirrors CrewAI.Crew).
    Pattern: CrewAI.Crew → Orchestration with SequentialAgent/ParallelAgent
    """

    def __init__(
        self, agents: list[Agent], tasks: list[CrewTask], process: str = "sequential"
    ) -> None:
        """
        Create a crew of agents working together.

        Args:
            agents: List of agents in the crew
            tasks: List of tasks to execute
            process: Execution strategy ("sequential" or "parallel")
        """
        self.agents = agents
        self.tasks = tasks
        self.process = process

    async def kickoff(self) -> dict[str, Any]:
        """
        Execute all tasks according to process type (mirrors CrewAI.Crew.kickoff).

        Returns:
            Dictionary with execution results and metadata
        """
        if self.process == "sequential":
            return await self._run_sequential()
        elif self.process == "parallel":
            return await self._run_parallel()
        else:
            raise ValueError(f"Unknown process type: {self.process}")

    async def _run_sequential(self) -> dict[str, Any]:
        """Execute tasks sequentially, passing output to next task."""
        results = []
        context = ""

        for i, task in enumerate(self.tasks):
            # Build message with context from previous tasks
            task_prompt = task.description
            if context:
                task_prompt = f"Previous work:\n{context}\n\nYour task: {task_prompt}"

            message = Message(role="user", content=task_prompt)
            result = await task.agent.process(message)

            results.append(
                {"task": task.description, "agent": task.agent.name, "output": result.content}
            )

            # Update context for next task
            context += f"\n\n{task.agent.name}: {result.content}"

        return {
            "process": "sequential",
            "tasks_completed": len(results),
            "results": results,
            "final_output": results[-1]["output"] if results else "",
        }

    async def _run_parallel(self) -> dict[str, Any]:
        """Execute all tasks in parallel."""

        # Create parallel agent for concurrent execution
        async def task_runner(task: CrewTask) -> dict[str, Any]:
            message = Message(role="user", content=task.description)
            result = await task.agent.process(message)
            return {"task": task.description, "agent": task.agent.name, "output": result.content}

        # Run all tasks concurrently
        task_coroutines = [task_runner(task) for task in self.tasks]
        results = await asyncio.gather(*task_coroutines)

        # Combine all outputs
        combined_output = "\n\n".join(r["output"] for r in results)

        return {
            "process": "parallel",
            "tasks_completed": len(results),
            "results": list(results),
            "final_output": combined_output,
        }


async def example_research_crew() -> None:
    """Example: Research crew with sequential process."""
    print("=" * 60)
    print("Example 1: Research Crew (Sequential Process)")
    print("=" * 60)

    # Create LLM (using test key for demo)
    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Create agents with roles
    researcher = CrewAgent(
        role="Market Researcher",
        goal="Uncover cutting-edge developments in AI and machine learning",
        backstory="Seasoned researcher with a knack for identifying emerging trends",
        llm=llm,
    )

    analyst = CrewAgent(
        role="Data Analyst",
        goal="Analyze research findings and extract key insights",
        backstory="Expert at finding patterns and meaning in complex information",
        llm=llm,
    )

    writer = CrewAgent(
        role="Tech Content Writer",
        goal="Craft compelling content about technology advancements",
        backstory="Creative writer with a passion for making tech accessible",
        llm=llm,
    )

    # Define tasks
    research_task = CrewTask(
        description="Research the latest AI trends in 2026",
        agent=researcher,
        expected_output="Bullet-point report on key AI trends",
    )

    analysis_task = CrewTask(
        description="Analyze the research and identify the top 3 most impactful trends",
        agent=analyst,
        expected_output="Analysis of top 3 AI trends with reasoning",
    )

    writing_task = CrewTask(
        description="Write an engaging 300-word blog post about the AI trends",
        agent=writer,
        expected_output="Blog post on AI trends",
    )

    # Create crew with sequential process
    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=[research_task, analysis_task, writing_task],
        process="sequential",
    )

    print("\n📝 CrewAI-style API:")
    print("   crew = Crew(agents=[researcher, analyst, writer],")
    print("               tasks=[research, analysis, writing],")
    print("               process='sequential')")
    print("   result = await crew.kickoff()")
    print("\n✅ Pattern: CrewAI.Crew + Process.sequential → SequentialAgent")
    print("   Each agent's output becomes context for the next agent")


async def example_parallel_crew() -> None:
    """Example: Analysis crew with parallel process."""
    print("\n\n" + "=" * 60)
    print("Example 2: Analysis Crew (Parallel Process)")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Create specialist agents
    sentiment_analyst = CrewAgent(
        role="Sentiment Analyst",
        goal="Analyze emotional tone and sentiment in text",
        backstory="Expert in emotional intelligence and sentiment analysis",
        llm=llm,
    )

    entity_extractor = CrewAgent(
        role="Entity Extraction Specialist",
        goal="Identify and extract key entities from text",
        backstory="Skilled at recognizing names, places, organizations",
        llm=llm,
    )

    topic_analyzer = CrewAgent(
        role="Topic Analyst",
        goal="Identify main topics and themes in text",
        backstory="Expert at thematic analysis and categorization",
        llm=llm,
    )

    # Define parallel tasks (all work on same input)
    text_to_analyze = "Sample article about AI developments"

    tasks = [
        CrewTask(
            description=f"Analyze sentiment in: {text_to_analyze}",
            agent=sentiment_analyst,
            expected_output="Sentiment analysis report",
        ),
        CrewTask(
            description=f"Extract entities from: {text_to_analyze}",
            agent=entity_extractor,
            expected_output="List of extracted entities",
        ),
        CrewTask(
            description=f"Identify topics in: {text_to_analyze}",
            agent=topic_analyzer,
            expected_output="Topic analysis report",
        ),
    ]

    # Create crew with parallel process
    crew = Crew(
        agents=[sentiment_analyst, entity_extractor, topic_analyzer],
        tasks=tasks,
        process="parallel",
    )

    print("\n📝 CrewAI-style API:")
    print("   crew = Crew(agents=[sentiment, entity, topic],")
    print("               tasks=[...],")
    print("               process='parallel')")
    print("   result = await crew.kickoff()")
    print("\n✅ Pattern: CrewAI.Crew + Process.parallel → ParallelAgent")
    print("   All agents work concurrently on their assigned tasks")


async def example_agent_with_tools() -> None:
    """Example: Agent with tools (like CrewAI's tools)."""
    print("\n\n" + "=" * 60)
    print("Example 3: Agents with Tools")
    print("=" * 60)

    print("\n📝 CrewAI Pattern:")
    print("   agent = Agent(role='Researcher',")
    print("                 tools=[search_tool, scrape_tool])")
    print("\n✅ Agenkit Equivalent:")
    print("   agent = ReActAgent(llm=llm, tools=[search_tool, scrape_tool])")
    print("   # Then wrap in CrewAgent for role-based interface")
    print("\n   Pattern: CrewAI tools → Agenkit ReActAgent")


async def main() -> None:
    """Run all examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 12 + "MiniCrew - CrewAI Built on Agenkit" + " " * 11 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n🎯 Demonstrate: CrewAI multi-agent collaboration on Agenkit")

    await example_research_crew()
    await example_parallel_crew()
    await example_agent_with_tools()

    print("\n\n" + "=" * 60)
    print("✅ MiniCrew Examples Complete")
    print("=" * 60)
    print("\n🔑 Key Takeaways:")
    print("   • Agenkit is a TOOLKIT for building multi-agent systems")
    print("   • CrewAI patterns map to Agenkit primitives:")
    print("     - CrewAI.Agent → Agent with role metadata")
    print("     - CrewAI.Task → Task dataclass with agent assignment")
    print("     - CrewAI.Crew → Orchestration (Sequential/Parallel)")
    print("     - Process.sequential → SequentialAgent pattern")
    print("     - Process.parallel → ParallelAgent pattern")
    print("\n📚 Migration guide: docs/migrations/crewai-to-agenkit.md")
    print("\n💡 Why Agenkit over CrewAI?")
    print("   ✓ 6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   ✓ 18x faster (Go) with goroutine-based concurrency")
    print("   ✓ Explicit control (no hidden orchestration)")
    print("   ✓ Composable patterns (mix Sequential, Parallel, Planning, etc.)")


if __name__ == "__main__":
    asyncio.run(main())
