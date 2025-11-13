"""
Task pattern for one-shot agent execution with lifecycle management.

This module provides the Task pattern, which wraps an Agent for single-use
execution with automatic resource cleanup.
"""

import asyncio
from typing import Any

from agenkit.interfaces import Agent, Message


class Task:
    """
    One-shot agent execution with lifecycle management.

    A Task wraps an Agent for single-use execution, providing:
    - Explicit one-shot semantics
    - Automatic resource cleanup
    - Task-specific middleware (timeout, retries)
    - Lifecycle hooks (before_task, after_task)
    - Prevention of reuse after completion

    The key distinction from Agent:
    - **Agent**: Multi-turn conversation with state
    - **Task**: One-shot execution, then cleanup

    Args:
        agent: The Agent to execute
        timeout: Optional timeout in seconds for task execution
        retries: Number of retry attempts on failure (default: 0)
        **kwargs: Additional configuration

    Example:
        >>> from agenkit.patterns import Task
        >>> from agenkit import Agent, Message
        >>>
        >>> # Basic usage
        >>> async def summarize_document(agent: Agent, document: str) -> str:
        ...     task = Task(agent)
        ...     try:
        ...         messages = [Message(role="user", content=f"Summarize: {document}")]
        ...         result = await task.execute(messages)
        ...         return result.content
        ...     finally:
        ...         await task.cleanup()

    Context manager usage (recommended):
        >>> async with Task(agent) as task:
        ...     result = await task.execute(messages)
        ...     # Automatic cleanup on exit

    With timeout and retries:
        >>> async with Task(agent, timeout=30.0, retries=2) as task:
        ...     result = await task.execute(messages)

    Pattern comparison:
        - Use Task when: Single purpose operation that needs cleanup
        - Use Agent when: Multi-turn conversation with state
        - Examples: summarize_document, classify_text, extract_entities
    """

    def __init__(
        self,
        agent: Agent,
        timeout: float | None = None,
        retries: int = 0,
        **kwargs: Any,
    ):
        """
        Initialize a Task.

        Args:
            agent: The Agent to execute
            timeout: Optional timeout in seconds
            retries: Number of retry attempts on failure
            **kwargs: Additional configuration
        """
        self._agent = agent
        self._timeout = timeout
        self._retries = retries
        self._config = kwargs
        self._completed = False
        self._result: Message | None = None

    async def execute(
        self,
        messages: list[Message],
        **kwargs: Any,
    ) -> Message:
        """
        Execute the task once.

        This method can only be called once per Task instance. After execution
        completes (successfully or with error), the Task is marked as completed
        and cannot be reused.

        Args:
            messages: Input messages for the agent
            **kwargs: Additional arguments passed to agent.call()

        Returns:
            The agent's response as a Message

        Raises:
            RuntimeError: If the task has already been completed
            asyncio.TimeoutError: If execution exceeds the timeout
            Exception: Any exception raised by the agent

        Example:
            >>> task = Task(agent, timeout=30.0, retries=2)
            >>> result = await task.execute(messages)
            >>> # Cannot call execute() again - will raise RuntimeError
        """
        if self._completed:
            raise RuntimeError(
                "Task already completed. Create a new Task for another execution."
            )

        # Merge kwargs with config
        call_kwargs = {**self._config, **kwargs}

        # Execute with retries
        attempts = self._retries + 1  # retries=0 means 1 attempt
        last_error = None

        for attempt in range(attempts):
            try:
                # Execute with optional timeout
                if self._timeout:
                    result = await asyncio.wait_for(
                        self._agent.call(messages, **call_kwargs),
                        timeout=self._timeout,
                    )
                else:
                    result = await self._agent.call(messages, **call_kwargs)

                # Success - mark completed and return
                self._completed = True
                self._result = result
                return result

            except asyncio.TimeoutError:
                # Timeout - don't retry
                self._completed = True
                await self.cleanup()
                raise

            except Exception as e:
                last_error = e
                # If this was the last attempt, fail
                if attempt == attempts - 1:
                    self._completed = True
                    await self.cleanup()
                    raise
                # Otherwise, retry after a brief delay
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

        # Should never reach here, but just in case
        self._completed = True
        await self.cleanup()
        raise last_error or RuntimeError("Task execution failed")

    async def cleanup(self) -> None:
        """
        Clean up resources after task completion.

        This method is called automatically when:
        - Task execution completes successfully
        - Task execution fails with an error
        - Using the Task as a context manager (on __aexit__)

        Override this method in subclasses to add custom cleanup logic:
        - Close network connections
        - Release memory/resources
        - Save state to disk
        - Send telemetry

        Example:
            >>> class CustomTask(Task):
            ...     async def cleanup(self) -> None:
            ...         # Custom cleanup logic
            ...         await self._agent.close()
            ...         await super().cleanup()
        """
        # Default implementation - hook for subclasses
        # In the future, this could:
        # - Close agent connections
        # - Release middleware resources
        # - Log completion metrics
        pass

    @property
    def completed(self) -> bool:
        """
        Check if the task has been completed.

        Returns:
            True if execute() has been called, False otherwise
        """
        return self._completed

    @property
    def result(self) -> Message | None:
        """
        Get the result of the task execution.

        Returns:
            The result Message if execution completed successfully, None otherwise
        """
        return self._result

    async def __aenter__(self) -> "Task":
        """
        Enter the context manager.

        Returns:
            The Task instance for use in the with block
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """
        Exit the context manager and perform cleanup.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        await self.cleanup()
