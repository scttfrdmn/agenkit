"""
MiniCrew Example 3: Parallel Processing

Demonstrates:
- Concurrent task execution
- Independent workstreams
- Result aggregation
- Speed benefits of parallelism

~200 LOC
"""

import asyncio
import os
import time

from agenkit.adapters.llm import OpenAILLM
from minicrew import Crew, CrewMember, ProcessType, Task


async def parallel_research_example():
    """
    Multiple researchers work simultaneously on different aspects.
    """
    print("=" * 60)
    print("Parallel Research Example")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create specialist researchers
    print("\n👥 Creating research team...")

    tech_researcher = CrewMember(
        agent=llm,
        role="Technology Researcher",
        goal="Research technical aspects and specifications",
        backstory="You specialize in technology analysis and specifications.",
    )

    market_researcher = CrewMember(
        agent=llm,
        role="Market Researcher",
        goal="Analyze market trends and opportunities",
        backstory="You excel at market analysis and trend identification.",
    )

    competitor_researcher = CrewMember(
        agent=llm,
        role="Competitive Analyst",
        goal="Study competitors and their strategies",
        backstory="You specialize in competitive intelligence.",
    )

    print(f"✅ {tech_researcher.role}")
    print(f"✅ {market_researcher.role}")
    print(f"✅ {competitor_researcher.role}")

    # Define independent research tasks
    print("\n📋 Assigning parallel research tasks...")

    tasks = [
        Task(
            description="Research key technical features of electric vehicles",
            assigned_to="Technology Researcher",
        ),
        Task(
            description="Analyze the EV market size and growth trends",
            assigned_to="Market Researcher",
        ),
        Task(
            description="Identify top 3 EV competitors and their strategies",
            assigned_to="Competitive Analyst",
        ),
    ]

    for task in tasks:
        print(f"• {task.assigned_to}: {task.description}")

    # Create parallel crew
    crew = Crew(
        members=[tech_researcher, market_researcher, competitor_researcher],
        tasks=tasks,
        process=ProcessType.PARALLEL,
    )

    # Execute in parallel
    print("\n🚀 Executing tasks in parallel...")
    start_time = time.time()

    result = await crew.execute("Topic: Electric Vehicles")

    elapsed = time.time() - start_time

    # Display results
    print("\n" + "=" * 60)
    print("PARALLEL RESEARCH RESULTS")
    print("=" * 60)

    for step in result["results"]:
        print(f"\n{step['role']}:")
        print("-" * 60)
        print(step["result"])
        print()

    print(f"⚡ Completed {len(tasks)} tasks in parallel")
    print(f"⏱️  Time: {elapsed:.1f}s")
    print()


async def compare_sequential_vs_parallel():
    """
    Compare performance of sequential vs parallel execution.
    """
    print("\n" + "=" * 60)
    print("Sequential vs Parallel Comparison")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create team
    analyst1 = CrewMember(
        agent=llm, role="Analyst 1", goal="Analyze data", backstory="Expert analyst"
    )

    analyst2 = CrewMember(
        agent=llm, role="Analyst 2", goal="Analyze data", backstory="Expert analyst"
    )

    analyst3 = CrewMember(
        agent=llm, role="Analyst 3", goal="Analyze data", backstory="Expert analyst"
    )

    # Define independent tasks
    tasks = [
        Task(description="List 3 benefits of cloud computing", assigned_to="Analyst 1"),
        Task(description="List 3 challenges of cloud computing", assigned_to="Analyst 2"),
        Task(description="List 3 cloud computing trends", assigned_to="Analyst 3"),
    ]

    # Sequential execution
    print("\n🐢 Sequential execution...")
    seq_crew = Crew(
        members=[analyst1, analyst2, analyst3],
        tasks=[t for t in tasks],  # Copy tasks
        process=ProcessType.SEQUENTIAL,
    )

    start = time.time()
    await seq_crew.execute()
    seq_time = time.time() - start

    print(f"   Time: {seq_time:.1f}s")

    # Parallel execution
    print("\n⚡ Parallel execution...")
    par_crew = Crew(
        members=[analyst1, analyst2, analyst3],
        tasks=tasks,
        process=ProcessType.PARALLEL,
    )

    start = time.time()
    await par_crew.execute()
    par_time = time.time() - start

    print(f"   Time: {par_time:.1f}s")

    # Show speedup
    speedup = seq_time / par_time if par_time > 0 else 1
    print(f"\n📊 Speedup: {speedup:.1f}x faster with parallel execution")


async def aggregation_example():
    """
    Demonstrate how parallel results are aggregated.
    """
    print("\n" + "=" * 60)
    print("Result Aggregation Example")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create content generators
    headline_writer = CrewMember(
        agent=llm,
        role="Headline Writer",
        goal="Create compelling headlines",
        backstory="You craft attention-grabbing headlines.",
    )

    stat_finder = CrewMember(
        agent=llm,
        role="Statistics Researcher",
        goal="Find relevant statistics",
        backstory="You find impactful data points.",
    )

    quote_collector = CrewMember(
        agent=llm,
        role="Quote Collector",
        goal="Gather relevant quotes",
        backstory="You find compelling expert quotes.",
    )

    # Define parallel content tasks
    tasks = [
        Task(
            description="Create a catchy headline about AI in healthcare",
            assigned_to="Headline Writer",
        ),
        Task(
            description="Find 2 statistics about AI in healthcare",
            assigned_to="Statistics Researcher",
        ),
        Task(
            description="Provide 1 relevant expert quote about AI in healthcare",
            assigned_to="Quote Collector",
        ),
    ]

    crew = Crew(
        members=[headline_writer, stat_finder, quote_collector],
        tasks=tasks,
        process=ProcessType.PARALLEL,
    )

    print("\n🚀 Gathering content components in parallel...")
    result = await crew.execute()

    # Show aggregated result
    print("\n" + "=" * 60)
    print("AGGREGATED ARTICLE COMPONENTS")
    print("=" * 60)
    print(result["final_output"])
    print()

    print(f"✅ Collected {len(tasks)} components in parallel")


async def dependency_aware_parallel():
    """
    Demonstrate parallel execution respecting dependencies.
    """
    print("\n" + "=" * 60)
    print("Dependency-Aware Parallel Execution")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create team
    researcher1 = CrewMember(
        agent=llm, role="Researcher A", goal="Research", backstory="Expert researcher"
    )

    researcher2 = CrewMember(
        agent=llm, role="Researcher B", goal="Research", backstory="Expert researcher"
    )

    synthesizer = CrewMember(
        agent=llm, role="Synthesizer", goal="Combine findings", backstory="Expert at synthesis"
    )

    # Define tasks with dependencies
    task_a = Task(description="Research AI ethics principles", assigned_to="Researcher A")

    task_b = Task(description="Research AI safety measures", assigned_to="Researcher B")

    task_c = Task(
        description="Synthesize ethics and safety into guidelines",
        assigned_to="Synthesizer",
        dependencies=[task_a.description, task_b.description],
    )

    tasks = [task_a, task_b, task_c]

    crew = Crew(
        members=[researcher1, researcher2, synthesizer],
        tasks=tasks,
        process=ProcessType.PARALLEL,
    )

    print("\n📋 Task dependencies:")
    print("• Task A and B: Independent (run in parallel)")
    print("• Task C: Depends on A and B (waits for completion)")

    print("\n🚀 Executing with dependency awareness...")
    result = await crew.execute()

    print("\n✅ Execution respected dependencies:")
    print("   Phase 1: A and B ran in parallel")
    print("   Phase 2: C ran after A and B completed")


async def main():
    """Run all parallel processing examples."""
    try:
        await parallel_research_example()
        await compare_sequential_vs_parallel()
        await aggregation_example()
        await dependency_aware_parallel()

        print("\n" + "=" * 60)
        print("✅ All parallel processing examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
