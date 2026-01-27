"""
MiniCrew - A CrewAI-inspired implementation using Agenkit primitives.

This demonstrates how CrewAI's abstractions (roles, tasks, crews) are just
orchestration patterns over agent coordination. Shows how Agenkit primitives
enable the same workflows without framework overhead.

Key insight: Multi-agent systems are just task orchestration + role assignment.

Core abstractions:
- CrewMember: Role-based agent with specific responsibilities
- Task: Unit of work with inputs, outputs, and dependencies
- Crew: Orchestrator managing multiple agents
- Process: Execution strategy (sequential, hierarchical, parallel)

~250-300 LOC total (implementation + examples)
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agenkit.interfaces import Agent, Message


class ProcessType(Enum):
    """Execution strategies for crew tasks."""

    SEQUENTIAL = "sequential"  # Execute tasks one by one
    HIERARCHICAL = "hierarchical"  # Manager assigns tasks
    PARALLEL = "parallel"  # Execute tasks concurrently


@dataclass
class CrewMember:
    """
    Role-based agent with specific responsibilities.

    A crew member has:
    - agent: The underlying Agenkit agent
    - role: Their function (e.g., "Researcher", "Writer")
    - goal: What they aim to achieve
    - backstory: Context for their personality/expertise
    """

    agent: Agent
    role: str
    goal: str
    backstory: str

    def __post_init__(self):
        """Create system message from role, goal, and backstory."""
        self.system_message = f"""You are a {self.role}.

Your goal: {self.goal}

Background: {self.backstory}

Always act according to your role and achieve your goal."""


@dataclass
class Task:
    """
    Unit of work with inputs, outputs, and dependencies.

    A task has:
    - description: What needs to be done
    - assigned_to: Which crew member should handle it
    - dependencies: Tasks that must complete first
    - context: Additional information from previous tasks
    - result: Output after execution
    """

    description: str
    assigned_to: str  # Role name
    dependencies: list[str] = field(default_factory=list)  # Task descriptions
    context: str = ""
    result: str = ""
    completed: bool = False

    def is_ready(self, completed_tasks: set[str]) -> bool:
        """Check if all dependencies are completed."""
        return all(dep in completed_tasks for dep in self.dependencies)


class Crew:
    """
    Orchestrator managing multiple agents.

    A crew coordinates crew members to complete tasks using different
    execution strategies (sequential, hierarchical, parallel).
    """

    def __init__(
        self,
        members: list[CrewMember],
        tasks: list[Task],
        process: ProcessType = ProcessType.SEQUENTIAL,
        manager: CrewMember | None = None,
    ):
        """
        Create a crew.

        Args:
            members: List of crew members
            tasks: List of tasks to complete
            process: Execution strategy
            manager: Optional manager for hierarchical process
        """
        if not members:
            raise ValueError("Crew requires at least one member")
        if not tasks:
            raise ValueError("Crew requires at least one task")

        self.members = {member.role: member for member in members}
        self.tasks = tasks
        self.process = process
        self.manager = manager

        # Validate task assignments
        for task in tasks:
            if task.assigned_to not in self.members:
                raise ValueError(f"Task assigned to unknown role: {task.assigned_to}")

    async def execute(self, initial_input: str = "") -> dict[str, Any]:
        """
        Execute all tasks according to process type.

        Args:
            initial_input: Starting input for the crew

        Returns:
            Dict with results and execution metadata
        """
        if self.process == ProcessType.SEQUENTIAL:
            return await self._execute_sequential(initial_input)
        elif self.process == ProcessType.HIERARCHICAL:
            return await self._execute_hierarchical(initial_input)
        elif self.process == ProcessType.PARALLEL:
            return await self._execute_parallel(initial_input)
        else:
            raise ValueError(f"Unknown process type: {self.process}")

    async def _execute_sequential(self, initial_input: str) -> dict[str, Any]:
        """
        Execute tasks sequentially in order.

        Each task receives the output of the previous task as context.
        """
        results = []
        completed_tasks = set()
        current_context = initial_input

        for task in self.tasks:
            # Wait for dependencies
            if not task.is_ready(completed_tasks):
                # Find and execute dependencies first
                for dep_desc in task.dependencies:
                    dep_task = next(t for t in self.tasks if t.description == dep_desc)
                    if not dep_task.completed:
                        await self._execute_task(dep_task, current_context)
                        completed_tasks.add(dep_task.description)

            # Execute task
            task.context = current_context
            result = await self._execute_task(task, current_context)

            # Update state
            task.result = result
            task.completed = True
            completed_tasks.add(task.description)
            current_context = result  # Next task gets this as context

            results.append(
                {
                    "task": task.description,
                    "role": task.assigned_to,
                    "result": result,
                }
            )

        return {
            "process": "sequential",
            "tasks_completed": len(results),
            "results": results,
            "final_output": current_context,
        }

    async def _execute_hierarchical(self, initial_input: str) -> dict[str, Any]:
        """
        Execute tasks with manager coordination.

        Manager reviews and approves each task output before proceeding.
        """
        if not self.manager:
            raise ValueError("Hierarchical process requires a manager")

        results = []
        completed_tasks = set()
        current_context = initial_input

        for task in self.tasks:
            # Execute task
            task.context = current_context
            result = await self._execute_task(task, current_context)

            # Manager review
            review_prompt = f"""Task: {task.description}
Assigned to: {task.assigned_to}
Output: {result}

As the manager, review this output. Is it acceptable? Provide feedback or approval."""

            review_message = Message(role="user", content=review_prompt)
            review_response = await self.manager.agent.process(review_message)
            review = str(review_response.content)

            # Update state
            task.result = result
            task.completed = True
            completed_tasks.add(task.description)
            current_context = result

            results.append(
                {
                    "task": task.description,
                    "role": task.assigned_to,
                    "result": result,
                    "manager_review": review,
                }
            )

        return {
            "process": "hierarchical",
            "tasks_completed": len(results),
            "results": results,
            "final_output": current_context,
        }

    async def _execute_parallel(self, initial_input: str) -> dict[str, Any]:
        """
        Execute independent tasks concurrently.

        Tasks with no dependencies run in parallel for speed.
        """
        results = []
        completed_tasks = set()

        # Group tasks by dependency level
        task_groups = self._group_by_dependencies()

        # Execute each group in parallel
        for group in task_groups:
            # Execute all tasks in this group concurrently
            group_results = await asyncio.gather(
                *[self._execute_task(task, initial_input) for task in group]
            )

            # Update state
            for task, result in zip(group, group_results):
                task.result = result
                task.completed = True
                completed_tasks.add(task.description)

                results.append(
                    {
                        "task": task.description,
                        "role": task.assigned_to,
                        "result": result,
                    }
                )

        # Aggregate all results
        final_output = "\n\n".join(r["result"] for r in results)

        return {
            "process": "parallel",
            "tasks_completed": len(results),
            "results": results,
            "final_output": final_output,
        }

    async def _execute_task(self, task: Task, context: str) -> str:
        """
        Execute a single task by the assigned crew member.

        Args:
            task: Task to execute
            context: Additional context from previous tasks

        Returns:
            Task result
        """
        member = self.members[task.assigned_to]

        # Build prompt with role context
        prompt = f"""{member.system_message}

Task: {task.description}

Context: {context if context else "No additional context"}

Complete this task according to your role and goal."""

        # Execute
        message = Message(role="user", content=prompt)
        response = await member.agent.process(message)

        return str(response.content)

    def _group_by_dependencies(self) -> list[list[Task]]:
        """
        Group tasks by dependency level for parallel execution.

        Returns:
            List of task groups, where each group can run in parallel
        """
        groups = []
        remaining = self.tasks.copy()
        completed = set()

        while remaining:
            # Find tasks with no pending dependencies
            ready = [t for t in remaining if t.is_ready(completed)]

            if not ready:
                raise ValueError("Circular dependency detected in tasks")

            groups.append(ready)

            # Mark as completed
            for task in ready:
                completed.add(task.description)
                remaining.remove(task)

        return groups


# Convenience functions for creating crew members with common roles


def create_researcher(agent: Agent) -> CrewMember:
    """Create a researcher crew member."""
    return CrewMember(
        agent=agent,
        role="Researcher",
        goal="Gather accurate information and validate sources",
        backstory="You are an experienced researcher with a keen eye for detail and credibility.",
    )


def create_writer(agent: Agent) -> CrewMember:
    """Create a writer crew member."""
    return CrewMember(
        agent=agent,
        role="Writer",
        goal="Create engaging, well-structured content",
        backstory="You are a skilled writer who crafts clear and compelling narratives.",
    )


def create_editor(agent: Agent) -> CrewMember:
    """Create an editor crew member."""
    return CrewMember(
        agent=agent,
        role="Editor",
        goal="Improve clarity, correctness, and quality",
        backstory="You are a meticulous editor who ensures excellence in every piece.",
    )


def create_manager(agent: Agent) -> CrewMember:
    """Create a manager crew member."""
    return CrewMember(
        agent=agent,
        role="Manager",
        goal="Coordinate team efforts and ensure quality outcomes",
        backstory="You are an experienced manager who guides teams to success.",
    )
