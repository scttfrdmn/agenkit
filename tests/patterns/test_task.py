"""
Tests for Task pattern - one-shot agent execution with lifecycle management.
"""

import asyncio

import pytest

from agenkit import Message
from agenkit.patterns import Task


# ============================================================================
# Mock Agents
# ============================================================================


class MockAgent:
    """Simple mock agent for testing."""

    def __init__(self, response="Success", delay=0):
        self.response = response
        self.delay = delay
        self.call_count = 0
        self.last_messages = None

    @property
    def name(self):
        return "mock_agent"

    @property
    def capabilities(self):
        return ["mock"]

    async def process(self, message: Message) -> Message:
        """Process message with optional delay."""
        self.call_count += 1
        self.last_messages = [message]

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        return Message(
            role="assistant",
            content=self.response,
            metadata={"call_count": self.call_count}
        )

    async def call(self, messages, **kwargs):
        """Agent.call interface for Task execution."""
        if not messages:
            raise ValueError("No messages provided")

        # Simulate processing
        return await self.process(messages[0])


class FailingAgent:
    """Agent that fails after N calls."""

    def __init__(self, fail_after=0):
        self.fail_after = fail_after
        self.call_count = 0

    @property
    def name(self):
        return "failing_agent"

    @property
    def capabilities(self):
        return ["fail"]

    async def process(self, message: Message) -> Message:
        """Fail after specified number of calls."""
        self.call_count += 1

        if self.call_count > self.fail_after:
            return Message(role="assistant", content="Success")

        raise RuntimeError(f"Failure #{self.call_count}")

    async def call(self, messages, **kwargs):
        """Agent.call interface."""
        return await self.process(messages[0])


# ============================================================================
# Task Creation Tests
# ============================================================================


def test_task_creation():
    """Test basic task creation."""
    agent = MockAgent()
    task = Task(agent)

    assert task._agent is agent
    assert task._timeout is None
    assert task._retries == 0
    assert not task.completed
    assert task.result is None


def test_task_with_timeout():
    """Test task creation with timeout."""
    agent = MockAgent()
    task = Task(agent, timeout=5.0)

    assert task._timeout == 5.0


def test_task_with_retries():
    """Test task creation with retries."""
    agent = MockAgent()
    task = Task(agent, retries=3)

    assert task._retries == 3


def test_task_with_custom_config():
    """Test task with additional configuration."""
    agent = MockAgent()
    task = Task(agent, timeout=10.0, retries=2, custom_param="value")

    assert task._timeout == 10.0
    assert task._retries == 2
    assert task._config["custom_param"] == "value"


# ============================================================================
# Task Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_task_execute_success():
    """Test successful task execution."""
    agent = MockAgent(response="Task complete")
    task = Task(agent)

    messages = [Message(role="user", content="Do task")]
    result = await task.execute(messages)

    assert result.role == "assistant"
    assert result.content == "Task complete"
    assert task.completed
    assert task.result is result
    assert agent.call_count == 1


@pytest.mark.asyncio
async def test_task_execute_only_once():
    """Test that task can only be executed once."""
    agent = MockAgent()
    task = Task(agent)

    messages = [Message(role="user", content="Do task")]

    # First execution succeeds
    await task.execute(messages)

    # Second execution raises
    with pytest.raises(RuntimeError, match="already completed"):
        await task.execute(messages)


@pytest.mark.asyncio
async def test_task_with_retries_success_first_try():
    """Test task with retries succeeds on first try."""
    agent = MockAgent(response="Success")
    task = Task(agent, retries=2)

    messages = [Message(role="user", content="Do task")]
    result = await task.execute(messages)

    assert result.content == "Success"
    assert agent.call_count == 1  # Only tried once


@pytest.mark.asyncio
async def test_task_with_retries_success_after_failures():
    """Test task retries after failures and eventually succeeds."""
    # Fail first 2 times, succeed on 3rd
    agent = FailingAgent(fail_after=2)
    task = Task(agent, retries=2)  # 3 total attempts

    messages = [Message(role="user", content="Do task")]
    result = await task.execute(messages)

    assert result.content == "Success"
    assert agent.call_count == 3  # 2 failures + 1 success


@pytest.mark.asyncio
async def test_task_with_retries_all_fail():
    """Test task fails after all retries exhausted."""
    agent = FailingAgent(fail_after=999)  # Always fails
    task = Task(agent, retries=2)

    messages = [Message(role="user", content="Do task")]

    with pytest.raises(RuntimeError):
        await task.execute(messages)

    assert task.completed
    assert agent.call_count == 3  # 3 attempts (retries + 1)


@pytest.mark.asyncio
async def test_task_timeout():
    """Test task timeout."""
    agent = MockAgent(delay=1.0)  # Takes 1 second
    task = Task(agent, timeout=0.1)  # Timeout after 0.1 seconds

    messages = [Message(role="user", content="Do task")]

    with pytest.raises(asyncio.TimeoutError):
        await task.execute(messages)

    assert task.completed


@pytest.mark.asyncio
async def test_task_no_timeout():
    """Test task without timeout completes successfully."""
    agent = MockAgent(delay=0.1)
    task = Task(agent)  # No timeout

    messages = [Message(role="user", content="Do task")]
    result = await task.execute(messages)

    assert result.content == "Success"
    assert task.completed


# ============================================================================
# Task Context Manager Tests
# ============================================================================


@pytest.mark.asyncio
async def test_task_context_manager():
    """Test task as async context manager."""
    agent = MockAgent(response="Context success")

    async with Task(agent) as task:
        messages = [Message(role="user", content="Do task")]
        result = await task.execute(messages)

        assert result.content == "Context success"
        assert task.completed


@pytest.mark.asyncio
async def test_task_context_manager_cleanup_on_error():
    """Test task context manager calls cleanup on error."""
    agent = FailingAgent(fail_after=0)
    task_ref = None

    try:
        async with Task(agent) as task:
            task_ref = task
            messages = [Message(role="user", content="Do task")]
            await task.execute(messages)
    except RuntimeError:
        pass  # Expected error

    # Task should still be marked completed even on error
    assert task_ref.completed


# ============================================================================
# Task Property Tests
# ============================================================================


def test_task_completed_property():
    """Test completed property."""
    agent = MockAgent()
    task = Task(agent)

    assert not task.completed
    assert task._completed == task.completed


def test_task_result_property_none():
    """Test result property when task not executed."""
    agent = MockAgent()
    task = Task(agent)

    assert task.result is None


@pytest.mark.asyncio
async def test_task_result_property_after_execution():
    """Test result property after execution."""
    agent = MockAgent(response="Final result")
    task = Task(agent)

    messages = [Message(role="user", content="Do task")]
    result = await task.execute(messages)

    assert task.result is result
    assert task.result.content == "Final result"


# ============================================================================
# Task Cleanup Tests
# ============================================================================


@pytest.mark.asyncio
async def test_task_cleanup_called():
    """Test cleanup method is called."""

    class CustomTask(Task):
        """Task with cleanup tracking."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.cleanup_called = False

        async def cleanup(self):
            """Track cleanup calls."""
            self.cleanup_called = True
            await super().cleanup()

    agent = MockAgent()
    task = CustomTask(agent)

    messages = [Message(role="user", content="Do task")]

    # Execute task
    async with task:
        await task.execute(messages)

    # Cleanup should have been called on __aexit__
    assert task.cleanup_called


# ============================================================================
# Task Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_task_multiple_sequential_tasks():
    """Test multiple sequential tasks with same agent."""
    agent = MockAgent()

    # First task
    task1 = Task(agent)
    messages1 = [Message(role="user", content="Task 1")]
    result1 = await task1.execute(messages1)

    assert result1.content == "Success"
    assert agent.call_count == 1

    # Second task
    task2 = Task(agent)
    messages2 = [Message(role="user", content="Task 2")]
    result2 = await task2.execute(messages2)

    assert result2.content == "Success"
    assert agent.call_count == 2  # Agent reused


@pytest.mark.asyncio
async def test_task_with_empty_messages():
    """Test task execution with empty messages list."""
    agent = MockAgent()
    task = Task(agent)

    with pytest.raises(ValueError, match="No messages"):
        await task.execute([])


@pytest.mark.asyncio
async def test_task_retry_backoff():
    """Test that retries use exponential backoff."""
    agent = FailingAgent(fail_after=999)
    task = Task(agent, retries=2)

    messages = [Message(role="user", content="Do task")]

    start_time = asyncio.get_event_loop().time()

    with pytest.raises(RuntimeError):
        await task.execute(messages)

    elapsed = asyncio.get_event_loop().time() - start_time

    # Backoff: 0.1s, 0.2s = 0.3s minimum
    # Allow some margin for execution time
    assert elapsed >= 0.2  # At least two backoffs happened
