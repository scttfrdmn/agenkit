"""Tests for retry middleware."""

import asyncio
import pytest

from agenkit.interfaces import Agent, Message
from agenkit.middleware import RetryConfig, RetryDecorator


class FailingAgent(Agent):
    """Agent that fails a specified number of times before succeeding."""

    def __init__(self, fail_count: int, success_msg: str, failure_msg: str):
        self.fail_count = fail_count
        self.attempts = 0
        self.success_msg = success_msg
        self.failure_msg = failure_msg

    @property
    def name(self) -> str:
        return "failing-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise Exception(self.failure_msg)
        return Message(role="agent", content=self.success_msg)


@pytest.mark.asyncio
async def test_retry_success():
    """Test successful retry after failures."""
    agent = FailingAgent(fail_count=2, success_msg="success after retries", failure_msg="temporary failure")

    retry = RetryDecorator(
        agent, RetryConfig(max_attempts=3, initial_backoff=0.01, backoff_multiplier=2.0)
    )

    msg = Message(role="user", content="test")
    response = await retry.process(msg)

    assert response.content == "success after retries"
    assert agent.attempts == 3


@pytest.mark.asyncio
async def test_retry_max_attempts_exceeded():
    """Test failure when max attempts exceeded."""
    agent = FailingAgent(fail_count=10, success_msg="should not succeed", failure_msg="persistent failure")

    retry = RetryDecorator(
        agent, RetryConfig(max_attempts=3, initial_backoff=0.01, backoff_multiplier=2.0)
    )

    msg = Message(role="user", content="test")

    with pytest.raises(Exception) as exc_info:
        await retry.process(msg)

    assert "Max retry attempts" in str(exc_info.value)
    assert agent.attempts == 3


@pytest.mark.asyncio
async def test_retry_immediate_success():
    """Test immediate success without retries."""
    agent = FailingAgent(fail_count=0, success_msg="immediate success", failure_msg="should not fail")

    retry = RetryDecorator(
        agent, RetryConfig(max_attempts=3, initial_backoff=0.01, backoff_multiplier=2.0)
    )

    msg = Message(role="user", content="test")
    response = await retry.process(msg)

    assert response.content == "immediate success"
    assert agent.attempts == 1


@pytest.mark.asyncio
async def test_retry_backoff_timing():
    """Test exponential backoff timing."""
    agent = FailingAgent(fail_count=3, success_msg="success", failure_msg="failure")

    retry = RetryDecorator(
        agent,
        RetryConfig(
            max_attempts=4, initial_backoff=0.1, max_backoff=1.0, backoff_multiplier=2.0
        ),
    )

    msg = Message(role="user", content="test")
    start = asyncio.get_event_loop().time()
    response = await retry.process(msg)
    elapsed = asyncio.get_event_loop().time() - start

    # Should have slept: 0.1 + 0.2 + 0.4 = 0.7 seconds
    assert elapsed >= 0.6  # Allow some tolerance
    assert response.content == "success"


@pytest.mark.asyncio
async def test_retry_max_backoff():
    """Test that backoff doesn't exceed max."""
    agent = FailingAgent(fail_count=5, success_msg="success", failure_msg="failure")

    retry = RetryDecorator(
        agent,
        RetryConfig(
            max_attempts=6, initial_backoff=0.1, max_backoff=0.2, backoff_multiplier=3.0
        ),
    )

    msg = Message(role="user", content="test")
    start = asyncio.get_event_loop().time()
    response = await retry.process(msg)
    elapsed = asyncio.get_event_loop().time() - start

    # Backoff sequence: 0.1, 0.2, 0.2, 0.2, 0.2 (capped at max_backoff)
    # Total: ~1.0 seconds
    assert elapsed >= 0.8  # Allow some tolerance
    assert response.content == "success"


@pytest.mark.asyncio
async def test_retry_should_retry_predicate():
    """Test custom should_retry predicate."""

    class CustomError(Exception):
        pass

    class OtherError(Exception):
        pass

    agent = FailingAgent(fail_count=1, success_msg="success", failure_msg="")

    # Only retry on CustomError
    def should_retry(error: Exception) -> bool:
        return isinstance(error, CustomError)

    # Agent that raises CustomError once
    class ConditionalAgent(Agent):
        def __init__(self):
            self.attempts = 0

        @property
        def name(self) -> str:
            return "conditional"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            self.attempts += 1
            if self.attempts == 1:
                raise CustomError("retryable")
            return Message(role="agent", content="success")

    agent_custom = ConditionalAgent()
    retry = RetryDecorator(
        agent_custom, RetryConfig(max_attempts=3, initial_backoff=0.01, should_retry=should_retry)
    )

    # Should succeed after retry
    msg = Message(role="user", content="test")
    response = await retry.process(msg)
    assert response.content == "success"
    assert agent_custom.attempts == 2


@pytest.mark.asyncio
async def test_retry_non_retryable_error():
    """Test that non-retryable errors are not retried."""

    class NonRetryableError(Exception):
        pass

    def should_retry(error: Exception) -> bool:
        return not isinstance(error, NonRetryableError)

    class NonRetryableAgent(Agent):
        def __init__(self):
            self.attempts = 0

        @property
        def name(self) -> str:
            return "non-retryable"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            self.attempts += 1
            raise NonRetryableError("do not retry")

    agent = NonRetryableAgent()
    retry = RetryDecorator(
        agent, RetryConfig(max_attempts=3, initial_backoff=0.01, should_retry=should_retry)
    )

    msg = Message(role="user", content="test")
    with pytest.raises(Exception) as exc_info:
        await retry.process(msg)

    assert "Non-retryable error" in str(exc_info.value)
    assert agent.attempts == 1  # Should only try once


@pytest.mark.asyncio
async def test_retry_config_validation():
    """Test that RetryConfig validates parameters."""
    # Test max_attempts < 1
    with pytest.raises(ValueError):
        RetryConfig(max_attempts=0)

    # Test initial_backoff <= 0
    with pytest.raises(ValueError):
        RetryConfig(initial_backoff=0)

    # Test max_backoff < initial_backoff
    with pytest.raises(ValueError):
        RetryConfig(initial_backoff=10.0, max_backoff=5.0)

    # Test backoff_multiplier <= 1.0
    with pytest.raises(ValueError):
        RetryConfig(backoff_multiplier=1.0)


@pytest.mark.asyncio
async def test_retry_decorator_name_capabilities():
    """Test that RetryDecorator passes through name and capabilities."""
    agent = FailingAgent(fail_count=0, success_msg="success", failure_msg="")
    retry = RetryDecorator(agent)

    assert retry.name == "failing-agent"
    assert retry.capabilities == []
