"""
MiniCrew Example 2: Hierarchical Process

Demonstrates:
- Manager-coordinated workflow
- Quality review at each step
- Task delegation
- Approval/feedback loops

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
    create_manager,
    create_researcher,
    create_writer,
)


async def manager_coordination_example():
    """
    Four-person team with manager oversight:
    Manager reviews each team member's output before proceeding.
    """
    print("=" * 60)
    print("Manager Coordination Example")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create team with manager
    print("\n👥 Creating managed team...")

    manager = create_manager(llm)
    researcher = create_researcher(llm)
    writer = create_writer(llm)
    editor = create_editor(llm)

    print(f"✅ {manager.role} (Oversees workflow)")
    print(f"✅ {researcher.role}")
    print(f"✅ {writer.role}")
    print(f"✅ {editor.role}")

    # Define tasks
    print("\n📋 Manager assigns tasks...")

    tasks = [
        Task(
            description="Research the benefits of renewable energy. Provide 3 key facts.",
            assigned_to="Researcher",
        ),
        Task(
            description="Write a persuasive paragraph about renewable energy adoption",
            assigned_to="Writer",
        ),
        Task(
            description="Edit for maximum impact and clarity",
            assigned_to="Editor",
        ),
    ]

    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task.assigned_to}: {task.description}")

    # Create hierarchical crew
    crew = Crew(
        members=[researcher, writer, editor],
        tasks=tasks,
        process=ProcessType.HIERARCHICAL,
        manager=manager,
    )

    # Execute with manager oversight
    print("\n🚀 Starting hierarchical workflow...")
    print("(Manager reviews each output)\n")

    result = await crew.execute("Focus: Benefits of renewable energy")

    # Display results with manager reviews
    print("=" * 60)
    print("WORKFLOW WITH MANAGER REVIEWS")
    print("=" * 60)

    for step in result["results"]:
        print(f"\n{step['role']}: {step['task']}")
        print("-" * 60)
        print(f"Output: {step['result']}")
        print()
        print(f"Manager Review: {step['manager_review']}")
        print()

    print("=" * 60)
    print("✅ All tasks approved by manager")
    print("=" * 60)


async def quality_assurance_example():
    """
    Manager ensures quality standards are met at each step.
    """
    print("\n" + "=" * 60)
    print("Quality Assurance Example")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    from minicrew import CrewMember

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create QA-focused manager
    qa_manager = CrewMember(
        agent=llm,
        role="QA Manager",
        goal="Ensure all outputs meet quality standards",
        backstory="You are a quality assurance expert who catches errors and ensures excellence.",
    )

    developer = CrewMember(
        agent=llm,
        role="Developer",
        goal="Write clean, correct code",
        backstory="You are a software developer who writes production-ready code.",
    )

    tester = CrewMember(
        agent=llm,
        role="Tester",
        goal="Validate code works correctly",
        backstory="You are a QA tester who finds edge cases and bugs.",
    )

    print(f"✅ {qa_manager.role}")
    print(f"✅ {developer.role}")
    print(f"✅ {tester.role}")

    # Define development workflow
    tasks = [
        Task(
            description="Write a Python function to validate email addresses",
            assigned_to="Developer",
        ),
        Task(
            description="Test the email validation function with 3 test cases",
            assigned_to="Tester",
        ),
    ]

    crew = Crew(
        members=[developer, tester],
        tasks=tasks,
        process=ProcessType.HIERARCHICAL,
        manager=qa_manager,
    )

    print("\n🚀 Starting QA workflow...")
    result = await crew.execute()

    # Display with QA reviews
    print("\n" + "=" * 60)
    print("CODE REVIEW PROCESS")
    print("=" * 60)

    for step in result["results"]:
        print(f"\n{step['role']}:")
        print(step["result"][:200] + "..." if len(step["result"]) > 200 else step["result"])
        print(f"\nQA Review: {step['manager_review'][:150]}...")
        print()


async def delegation_example():
    """
    Manager delegates tasks based on crew member expertise.
    """
    print("\n" + "=" * 60)
    print("Task Delegation Example")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    from minicrew import CrewMember

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Create diverse team
    manager = CrewMember(
        agent=llm,
        role="Project Manager",
        goal="Coordinate team efforts for project success",
        backstory="You excel at matching tasks to team member strengths.",
    )

    analyst = CrewMember(
        agent=llm,
        role="Business Analyst",
        goal="Understand requirements and document specifications",
        backstory="You translate business needs into clear requirements.",
    )

    architect = CrewMember(
        agent=llm,
        role="Solutions Architect",
        goal="Design scalable technical solutions",
        backstory="You create robust system designs.",
    )

    print(f"✅ {manager.role}")
    print(f"✅ {analyst.role}")
    print(f"✅ {architect.role}")

    # Define project tasks
    tasks = [
        Task(
            description="Document requirements for a user authentication system",
            assigned_to="Business Analyst",
        ),
        Task(
            description="Design the architecture for the authentication system",
            assigned_to="Solutions Architect",
        ),
    ]

    crew = Crew(
        members=[analyst, architect],
        tasks=tasks,
        process=ProcessType.HIERARCHICAL,
        manager=manager,
    )

    print("\n🚀 Manager delegates tasks...")
    result = await crew.execute("Project: User Authentication System")

    # Show delegation and review
    print("\n" + "=" * 60)
    print("PROJECT COORDINATION")
    print("=" * 60)

    for i, step in enumerate(result["results"], 1):
        print(f"\nPhase {i}: {step['role']}")
        print(f"Task: {step['task']}")
        print(f"Status: ✅ Completed")
        print(f"Manager feedback: {step['manager_review'][:100]}...")
        print()


async def main():
    """Run all hierarchical process examples."""
    try:
        await manager_coordination_example()
        await quality_assurance_example()
        await delegation_example()

        print("=" * 60)
        print("✅ All hierarchical process examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
