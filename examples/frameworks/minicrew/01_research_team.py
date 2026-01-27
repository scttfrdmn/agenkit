"""
MiniCrew Example 1: Research Team

Demonstrates:
- Sequential process (Researcher → Writer → Editor)
- Role-based agents with specific expertise
- Task dependencies and context passing
- Complete content generation workflow

~200 LOC
"""

import asyncio
import os

from agenkit.adapters.llm import OpenAILLM
from minicrew import (
    Crew,
    ProcessType,
    Task,
    create_editor,
    create_researcher,
    create_writer,
)


async def research_team_example():
    """
    Three-person research team:
    1. Researcher gathers information
    2. Writer creates article
    3. Editor polishes final output
    """
    print("=" * 60)
    print("Research Team Example")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    # Create LLM
    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create crew members
    print("\n👥 Creating crew members...")
    researcher = create_researcher(llm)
    writer = create_writer(llm)
    editor = create_editor(llm)

    print(f"✅ {researcher.role}: {researcher.goal}")
    print(f"✅ {writer.role}: {writer.goal}")
    print(f"✅ {editor.role}: {editor.goal}")

    # Define tasks
    print("\n📋 Defining tasks...")
    tasks = [
        Task(
            description="Research key facts about quantum computing and list 3 main points",
            assigned_to="Researcher",
        ),
        Task(
            description="Write a 150-word blog post about quantum computing using the research",
            assigned_to="Writer",
        ),
        Task(
            description="Edit the blog post for clarity and engagement",
            assigned_to="Editor",
        ),
    ]

    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task.assigned_to}: {task.description}")

    # Create crew with sequential process
    crew = Crew(
        members=[researcher, writer, editor],
        tasks=tasks,
        process=ProcessType.SEQUENTIAL,
    )

    # Execute
    print("\n🚀 Starting research team workflow...")
    print()

    result = await crew.execute("Topic: Quantum Computing")

    # Display results
    print("=" * 60)
    print("WORKFLOW RESULTS")
    print("=" * 60)

    for step in result["results"]:
        print(f"\n{step['role']}: {step['task']}")
        print("-" * 60)
        print(step["result"])

    print("\n" + "=" * 60)
    print("FINAL OUTPUT")
    print("=" * 60)
    print(result["final_output"])
    print()

    print(f"✅ Completed {result['tasks_completed']} tasks using {result['process']} process")


async def specialized_roles_example():
    """
    Demonstrate custom specialized roles beyond the defaults.
    """
    print("\n" + "=" * 60)
    print("Specialized Roles Example")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    from minicrew import CrewMember

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create specialized roles
    print("\n👥 Creating specialized crew...")

    data_analyst = CrewMember(
        agent=llm,
        role="Data Analyst",
        goal="Extract insights from data and identify trends",
        backstory="You are a data scientist with expertise in statistical analysis.",
    )

    strategist = CrewMember(
        agent=llm,
        role="Business Strategist",
        goal="Transform insights into actionable business strategies",
        backstory="You are a strategic consultant with 15 years of experience.",
    )

    presenter = CrewMember(
        agent=llm,
        role="Presentation Designer",
        goal="Create compelling executive summaries",
        backstory="You craft presentations that influence C-suite decisions.",
    )

    print(f"✅ {data_analyst.role}")
    print(f"✅ {strategist.role}")
    print(f"✅ {presenter.role}")

    # Define analysis workflow
    tasks = [
        Task(
            description="Analyze this data: Revenue +40%, Customers +25%, Churn -15%. What are the 2 key insights?",
            assigned_to="Data Analyst",
        ),
        Task(
            description="Based on the data insights, recommend 2 strategic priorities for next quarter",
            assigned_to="Business Strategist",
        ),
        Task(
            description="Create a 3-bullet executive summary of the analysis and strategy",
            assigned_to="Presentation Designer",
        ),
    ]

    crew = Crew(
        members=[data_analyst, strategist, presenter],
        tasks=tasks,
        process=ProcessType.SEQUENTIAL,
    )

    print("\n🚀 Starting analysis workflow...")
    result = await crew.execute()

    # Display results
    print("\n" + "=" * 60)
    print("EXECUTIVE SUMMARY")
    print("=" * 60)
    print(result["final_output"])
    print()


async def context_passing_example():
    """
    Demonstrate how context flows between tasks.
    """
    print("\n" + "=" * 60)
    print("Context Passing Example")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create crew
    researcher = create_researcher(llm)
    writer = create_writer(llm)

    tasks = [
        Task(
            description="Find 2 interesting facts about Mars",
            assigned_to="Researcher",
        ),
        Task(
            description="Write a haiku incorporating these Mars facts",
            assigned_to="Writer",
        ),
    ]

    crew = Crew(
        members=[researcher, writer],
        tasks=tasks,
        process=ProcessType.SEQUENTIAL,
    )

    print("\n🚀 Executing workflow with context passing...")
    result = await crew.execute()

    # Show how context flows
    print("\n📊 Context Flow:")
    print()

    for i, step in enumerate(result["results"], 1):
        print(f"Step {i} - {step['role']}:")
        print(f"Output: {step['result'][:100]}...")
        if i < len(result["results"]):
            print("    ↓ (passed as context)")
        print()

    print("=" * 60)
    print("FINAL HAIKU")
    print("=" * 60)
    print(result["final_output"])
    print()


async def main():
    """Run all research team examples."""
    try:
        await research_team_example()
        await specialized_roles_example()
        await context_passing_example()

        print("=" * 60)
        print("✅ All research team examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
