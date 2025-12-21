"""
Prioritization Composition

A simple priority queue for task management with custom priority functions.
This demonstrates that "prioritization" is just a heap-based task queue.

For production task management systems with dependencies, scheduling,
and resource allocation, build a custom pattern or use a dedicated
task queue system (Celery, RQ, etc.).

This composition is perfect for:
- Simple task ordering
- Learning priority queue patterns
- Quick prototypes
- Non-distributed systems

References:
    Source: Gulli "Agentic Design Patterns" (2025)
    Pattern: Could be combined with PlanningAgent for task execution

Example:
    Basic usage::

        from agenkit.techniques.compositions import TaskQueue
        from agenkit import Message

        queue = TaskQueue(priority_fn=lambda task: task.get("urgency", 0))

        queue.add_task({"name": "Low priority", "urgency": 1})
        queue.add_task({"name": "High priority", "urgency": 10})

        # Process highest priority first
        while not queue.is_empty():
            task = queue.get_next_task()
            await process_task(task)
"""

import heapq
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class PrioritizedTask:
    """
    Task with priority for heap queue.

    Attributes:
        priority: Priority score (higher = more important)
        task: The actual task data
        task_id: Unique task identifier
    """
    priority: float
    task: Any = field(compare=False)
    task_id: int = field(compare=False)


class TaskQueue:
    """
    Simple priority queue for task management.

    This is a minimal composition (~50 LOC) showing that prioritization
    is just a heap-based queue with custom priority function.

    For production task systems, consider:
    - Distributed task queues (Celery, RQ)
    - Dependency management
    - Resource allocation
    - Retry logic and error handling
    - Persistent storage

    Attributes:
        priority_fn: Function to compute task priority
        queue: Internal heap queue
        task_counter: Counter for unique task IDs
    """

    def __init__(
        self,
        priority_fn: Callable[[Any], float] | None = None
    ):
        """
        Initialize task queue.

        Args:
            priority_fn: Function that takes a task and returns priority score.
                Higher scores = higher priority. If None, uses default priority
                of 0 for all tasks (FIFO order).

        Example:
            >>> def urgency_priority(task: dict) -> float:
            ...     return task.get("urgency", 0)
            >>>
            >>> queue = TaskQueue(priority_fn=urgency_priority)
        """
        self.priority_fn = priority_fn or (lambda x: 0)
        self.queue: list[PrioritizedTask] = []
        self.task_counter = 0

    def add_task(self, task: Any) -> int:
        """
        Add task to queue.

        Args:
            task: Task to add (can be any type)

        Returns:
            Task ID for tracking

        Example:
            >>> task_id = queue.add_task({"name": "Important task", "urgency": 10})
        """
        priority = self.priority_fn(task)
        task_id = self.task_counter
        self.task_counter += 1

        # Use negative priority for max-heap (Python heapq is min-heap)
        prioritized = PrioritizedTask(
            priority=-priority,  # Negative for max-heap
            task=task,
            task_id=task_id
        )

        heapq.heappush(self.queue, prioritized)
        return task_id

    def get_next_task(self) -> Any | None:
        """
        Get highest priority task from queue.

        Returns:
            Highest priority task, or None if queue is empty

        Example:
            >>> task = queue.get_next_task()
            >>> if task:
            ...     await process(task)
        """
        if not self.queue:
            return None

        prioritized = heapq.heappop(self.queue)
        return prioritized.task

    def peek_next_task(self) -> Any | None:
        """
        View highest priority task without removing it.

        Returns:
            Highest priority task, or None if queue is empty
        """
        if not self.queue:
            return None

        return self.queue[0].task

    def is_empty(self) -> bool:
        """
        Check if queue is empty.

        Returns:
            True if queue has no tasks
        """
        return len(self.queue) == 0

    def size(self) -> int:
        """
        Get number of tasks in queue.

        Returns:
            Number of pending tasks
        """
        return len(self.queue)

    def clear(self):
        """Remove all tasks from queue."""
        self.queue.clear()

    def get_all_tasks(self) -> list[Any]:
        """
        Get all tasks in priority order without removing them.

        Returns:
            List of tasks in priority order (highest first)

        Note:
            This creates a copy of the queue to avoid modifying it.
        """
        # Create sorted copy without modifying original
        sorted_queue = sorted(self.queue)
        return [item.task for item in sorted_queue]


class PriorityTaskExecutor:
    """
    Executor that processes tasks from a priority queue.

    This combines TaskQueue with async execution for a complete
    prioritization composition.

    Example:
        >>> async def process_fn(task):
        ...     print(f"Processing: {task['name']}")
        >>>
        >>> executor = PriorityTaskExecutor(
        ...     priority_fn=lambda t: t.get("urgency", 0),
        ...     process_fn=process_fn
        ... )
        >>>
        >>> executor.add_task({"name": "Task 1", "urgency": 5})
        >>> executor.add_task({"name": "Task 2", "urgency": 10})
        >>> await executor.execute_all()
    """

    def __init__(
        self,
        priority_fn: Callable[[Any], float] | None = None,
        process_fn: Callable[[Any], Any] | None = None
    ):
        """
        Initialize priority task executor.

        Args:
            priority_fn: Function to compute task priority
            process_fn: Async function to process each task
        """
        self.queue = TaskQueue(priority_fn=priority_fn)
        self.process_fn = process_fn

    def add_task(self, task: Any) -> int:
        """Add task to queue."""
        return self.queue.add_task(task)

    async def execute_all(self) -> list[Any]:
        """
        Execute all tasks in priority order.

        Returns:
            List of results from processing each task
        """
        results = []

        while not self.queue.is_empty():
            task = self.queue.get_next_task()

            if self.process_fn:
                result = await self.process_fn(task)
                results.append(result)

        return results

    async def execute_n(self, n: int) -> list[Any]:
        """
        Execute up to n highest priority tasks.

        Args:
            n: Maximum number of tasks to execute

        Returns:
            List of results from processing tasks
        """
        results = []

        for _ in range(n):
            if self.queue.is_empty():
                break

            task = self.queue.get_next_task()

            if self.process_fn:
                result = await self.process_fn(task)
                results.append(result)

        return results
