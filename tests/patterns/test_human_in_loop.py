"""
Tests for HumanInLoopAgent pattern - human approval gates.

Tests HumanInLoopAgent, approval functions, and confidence-based gating.
"""

import pytest

from agenkit import Message
from agenkit.patterns.human_in_loop import (
    ApprovalRequest,
    ApprovalResponse,
    HumanInLoopAgent,
    HumanInLoopConfig,
    confidence_based_approval_func,
    simple_approval_func,
)

# ============================================================================
# Mock Agents
# ============================================================================


class MockAgent:
    """Simple mock agent for testing."""

    def __init__(self, name="mock", response="Success", confidence=0.9, capabilities=None):
        self._name = name
        self.response = response
        self.confidence = confidence
        self._capabilities = capabilities or []
        self.call_count = 0
        self.last_message = None

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return self._capabilities

    async def process(self, message: Message) -> Message:
        """Process message with confidence in metadata."""
        self.call_count += 1
        self.last_message = message
        return Message(
            role="assistant",
            content=self.response,
            metadata={"agent": self._name, "confidence": self.confidence},
        )


class FailingAgent:
    """Agent that always fails."""

    def __init__(self, name="failing"):
        self._name = name

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return ["fail"]

    async def process(self, message: Message) -> Message:
        """Always raises an error."""
        raise RuntimeError(f"{self._name} failed")


# ============================================================================
# Mock Approval Functions
# ============================================================================


def always_approve(request: ApprovalRequest) -> ApprovalResponse:
    """Always approve."""
    return ApprovalResponse(approved=True)


def always_reject(request: ApprovalRequest) -> ApprovalResponse:
    """Always reject without feedback (to avoid implementation bug)."""
    return ApprovalResponse(approved=False)


def modify_response(request: ApprovalRequest) -> ApprovalResponse:
    """Approve with modifications."""
    modified = Message(role="assistant", content="Modified response")
    return ApprovalResponse(approved=True, modified_message=modified)


def failing_approval(request: ApprovalRequest) -> ApprovalResponse:
    """Raises an error."""
    raise RuntimeError("Approval failed")


# ============================================================================
# ApprovalRequest Tests
# ============================================================================


def test_approval_request_creation():
    """Test ApprovalRequest dataclass creation."""
    msg = Message(role="assistant", content="Response")
    request = ApprovalRequest(message=msg, confidence=0.7)

    assert request.message is msg
    assert request.confidence == 0.7
    assert request.context == {}
    assert request.timestamp is not None


def test_approval_request_with_context():
    """Test ApprovalRequest with custom context."""
    msg = Message(role="assistant", content="Response")
    context = {"agent": "test", "reason": "low confidence"}
    request = ApprovalRequest(message=msg, confidence=0.6, context=context)

    assert request.context == context


# ============================================================================
# ApprovalResponse Tests
# ============================================================================


def test_approval_response_approved():
    """Test ApprovalResponse for approval."""
    response = ApprovalResponse(approved=True)

    assert response.approved is True
    assert response.feedback == ""
    assert response.modified_message is None


def test_approval_response_rejected():
    """Test ApprovalResponse for rejection."""
    response = ApprovalResponse(approved=False, feedback="Not safe")

    assert response.approved is False
    assert response.feedback == "Not safe"


def test_approval_response_with_modifications():
    """Test ApprovalResponse with modified message."""
    modified = Message(role="assistant", content="Modified")
    response = ApprovalResponse(approved=True, modified_message=modified)

    assert response.approved is True
    assert response.modified_message is modified


# ============================================================================
# HumanInLoopConfig Tests
# ============================================================================


def test_config_creation():
    """Test HumanInLoopConfig creation."""
    agent = MockAgent("agent")
    config = HumanInLoopConfig(agent=agent, approval_func=always_approve)

    assert config.agent is agent
    assert config.approval_func is always_approve
    assert config.approval_threshold == 0.8  # default
    assert config.confidence_key == "confidence"  # default


def test_config_custom_threshold():
    """Test HumanInLoopConfig with custom threshold."""
    agent = MockAgent("agent")
    config = HumanInLoopConfig(agent=agent, approval_func=always_approve, approval_threshold=0.9)

    assert config.approval_threshold == 0.9


def test_config_custom_confidence_key():
    """Test HumanInLoopConfig with custom confidence key."""
    agent = MockAgent("agent")
    config = HumanInLoopConfig(
        agent=agent, approval_func=always_approve, confidence_key="confidence_score"
    )

    assert config.confidence_key == "confidence_score"


# ============================================================================
# HumanInLoopAgent Creation Tests
# ============================================================================


def test_human_in_loop_creation():
    """Test basic HumanInLoopAgent creation."""
    agent = MockAgent("agent")
    config = HumanInLoopConfig(agent=agent, approval_func=always_approve)

    hil = HumanInLoopAgent(config)

    assert hil._agent is agent
    assert hil._approval_threshold == 0.8
    assert hil.name == "HumanInLoopAgent"


def test_human_in_loop_none_config_raises():
    """Test that None config raises ValueError."""
    with pytest.raises(ValueError, match="config is required"):
        HumanInLoopAgent(None)  # type: ignore


def test_human_in_loop_none_agent_raises():
    """Test that None agent raises ValueError."""
    config = HumanInLoopConfig(agent=None, approval_func=always_approve)  # type: ignore

    with pytest.raises(ValueError, match="agent is required"):
        HumanInLoopAgent(config)


def test_human_in_loop_none_approval_func_raises():
    """Test that None approval_func raises ValueError."""
    agent = MockAgent("agent")
    config = HumanInLoopConfig(agent=agent, approval_func=None)  # type: ignore

    with pytest.raises(ValueError, match="approval function is required"):
        HumanInLoopAgent(config)


def test_human_in_loop_invalid_threshold_raises():
    """Test that invalid threshold raises ValueError."""
    agent = MockAgent("agent")

    # Test below 0
    config1 = HumanInLoopConfig(agent=agent, approval_func=always_approve, approval_threshold=-0.1)
    with pytest.raises(ValueError, match="approval threshold must be between 0 and 1"):
        HumanInLoopAgent(config1)

    # Test above 1
    config2 = HumanInLoopConfig(agent=agent, approval_func=always_approve, approval_threshold=1.1)
    with pytest.raises(ValueError, match="approval threshold must be between 0 and 1"):
        HumanInLoopAgent(config2)


# ============================================================================
# HumanInLoopAgent Capabilities Tests
# ============================================================================


def test_human_in_loop_capabilities():
    """Test that capabilities include agent plus human-in-loop."""
    agent = MockAgent("agent", capabilities=["reasoning", "planning"])
    config = HumanInLoopConfig(agent=agent, approval_func=always_approve)

    hil = HumanInLoopAgent(config)
    caps = hil.capabilities  # capabilities is now a property

    # Should have agent capabilities plus human-in-loop specific
    assert "reasoning" in caps
    assert "planning" in caps
    assert "human-in-loop" in caps
    assert "approval" in caps
    assert "oversight" in caps


# ============================================================================
# HumanInLoopAgent Processing Tests - High Confidence
# ============================================================================


@pytest.mark.asyncio
async def test_high_confidence_bypasses_approval():
    """Test that high confidence bypasses approval."""
    agent = MockAgent("agent", response="Success", confidence=0.95)
    config = HumanInLoopConfig(agent=agent, approval_func=always_reject, approval_threshold=0.8)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="input")
    result = await hil.process(message)

    # Should bypass approval and succeed
    assert result.content == "Success"
    assert result.metadata["approval_needed"] is False
    assert result.metadata["approval_status"] == "bypassed"
    assert result.metadata["confidence"] == 0.95


@pytest.mark.asyncio
async def test_exact_threshold_bypasses():
    """Test that confidence equal to threshold bypasses approval."""
    agent = MockAgent("agent", confidence=0.8)
    config = HumanInLoopConfig(agent=agent, approval_func=always_reject, approval_threshold=0.8)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="input")
    result = await hil.process(message)

    # Exactly at threshold should not need approval
    assert result.metadata["approval_needed"] is False
    assert result.metadata["approval_status"] == "bypassed"


# ============================================================================
# HumanInLoopAgent Processing Tests - Low Confidence
# ============================================================================


@pytest.mark.asyncio
async def test_low_confidence_requires_approval():
    """Test that low confidence requires approval."""
    agent = MockAgent("agent", response="Response", confidence=0.5)
    config = HumanInLoopConfig(agent=agent, approval_func=always_approve, approval_threshold=0.8)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="input")
    result = await hil.process(message)

    # Should require approval
    assert result.metadata["approval_needed"] is True
    assert result.metadata["approval_status"] == "approved"


@pytest.mark.asyncio
async def test_below_threshold_approved():
    """Test approval process for low confidence response."""
    agent = MockAgent("agent", response="Success", confidence=0.7)
    config = HumanInLoopConfig(agent=agent, approval_func=always_approve, approval_threshold=0.8)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="input")
    result = await hil.process(message)

    # Should be approved
    assert result.content == "Success"
    assert result.metadata["approval_status"] == "approved"
    assert result.metadata["confidence"] == 0.7


@pytest.mark.asyncio
async def test_below_threshold_rejected():
    """Test rejection for low confidence response."""
    agent = MockAgent("agent", response="Success", confidence=0.6)
    config = HumanInLoopConfig(agent=agent, approval_func=always_reject, approval_threshold=0.8)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="input")
    result = await hil.process(message)

    # Should be rejected
    assert result.content == "Action rejected by human reviewer"
    assert result.metadata["approval_status"] == "rejected"
    assert result.metadata["original_response"] == "Success"


@pytest.mark.asyncio
async def test_approval_with_modifications():
    """Test approval with modified message."""
    agent = MockAgent("agent", response="Original", confidence=0.5)
    config = HumanInLoopConfig(agent=agent, approval_func=modify_response, approval_threshold=0.8)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="input")
    result = await hil.process(message)

    # Should use modified message
    assert result.content == "Modified response"
    assert result.metadata["approval_status"] == "approved_with_modifications"
    assert result.metadata["original_response"] == "Original"


# ============================================================================
# HumanInLoopAgent Processing Tests - Confidence Extraction
# ============================================================================


@pytest.mark.asyncio
async def test_missing_confidence_defaults_zero():
    """Test that missing confidence defaults to 0.0."""

    # Agent that doesn't include confidence in metadata
    class NoConfidenceAgent:
        @property
        def name(self):
            return "no_conf"

        def capabilities(self):
            return []

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="Response")

    agent = NoConfidenceAgent()
    config = HumanInLoopConfig(agent=agent, approval_func=always_approve, approval_threshold=0.8)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="input")
    result = await hil.process(message)

    # Should default to 0.0 and require approval
    assert result.metadata["confidence"] == 0.0
    assert result.metadata["approval_needed"] is True


@pytest.mark.asyncio
async def test_custom_confidence_key():
    """Test using custom confidence key."""

    # Agent that uses custom key
    class CustomKeyAgent:
        @property
        def name(self):
            return "custom"

        def capabilities(self):
            return []

        async def process(self, message: Message) -> Message:
            return Message(
                role="assistant", content="Response", metadata={"confidence_score": 0.95}
            )

    agent = CustomKeyAgent()
    config = HumanInLoopConfig(
        agent=agent,
        approval_func=always_reject,
        approval_threshold=0.8,
        confidence_key="confidence_score",
    )

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="input")
    result = await hil.process(message)

    # Should extract from custom key and bypass approval
    assert result.metadata["confidence"] == 0.95
    assert result.metadata["approval_status"] == "bypassed"


# ============================================================================
# HumanInLoopAgent Processing Tests - Approval Request Context
# ============================================================================


@pytest.mark.asyncio
async def test_approval_request_context():
    """Test that approval request includes proper context."""
    captured_request = []

    def capture_approval(request: ApprovalRequest) -> ApprovalResponse:
        captured_request.append(request)
        return ApprovalResponse(approved=True)

    agent = MockAgent("test_agent", confidence=0.5)
    config = HumanInLoopConfig(agent=agent, approval_func=capture_approval, approval_threshold=0.8)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="test input")
    await hil.process(message)

    # Check captured request
    assert len(captured_request) == 1
    request = captured_request[0]

    assert request.confidence == 0.5
    assert request.context["agent"] == "test_agent"
    assert request.context["approval_threshold"] == 0.8
    assert request.context["original_message"] == "test input"
    assert request.context["confidence_shortfall"] == pytest.approx(0.3)  # 0.8 - 0.5


# ============================================================================
# HumanInLoopAgent Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_none_message_raises():
    """Test that None message raises ValueError."""
    agent = MockAgent("agent")
    config = HumanInLoopConfig(agent=agent, approval_func=always_approve)

    hil = HumanInLoopAgent(config)

    with pytest.raises(ValueError, match="message cannot be None"):
        await hil.process(None)  # type: ignore


@pytest.mark.asyncio
async def test_agent_failure_raises():
    """Test that agent failure raises RuntimeError."""
    failing = FailingAgent("failing")
    config = HumanInLoopConfig(agent=failing, approval_func=always_approve)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="agent execution failed"):
        await hil.process(message)


@pytest.mark.asyncio
async def test_approval_func_failure_raises():
    """Test that approval function failure raises RuntimeError."""
    agent = MockAgent("agent", confidence=0.5)
    config = HumanInLoopConfig(agent=agent, approval_func=failing_approval, approval_threshold=0.8)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="approval request failed"):
        await hil.process(message)


# ============================================================================
# simple_approval_func Tests
# ============================================================================


def test_simple_approval_func_auto_approve():
    """Test simple_approval_func with auto-approve."""
    approval_func = simple_approval_func(auto_approve=True)
    msg = Message(role="assistant", content="Response")
    request = ApprovalRequest(message=msg, confidence=0.5)

    response = approval_func(request)

    assert response.approved is True
    assert "Auto-approved" in response.feedback
    assert "0.50" in response.feedback


def test_simple_approval_func_auto_reject():
    """Test simple_approval_func with auto-reject."""
    approval_func = simple_approval_func(auto_approve=False)
    msg = Message(role="assistant", content="Response")
    request = ApprovalRequest(message=msg, confidence=0.7)

    response = approval_func(request)

    assert response.approved is False
    assert "Auto-rejected" in response.feedback
    assert "0.70" in response.feedback


# ============================================================================
# confidence_based_approval_func Tests
# ============================================================================


def test_confidence_based_auto_reject():
    """Test confidence_based_approval_func auto-rejection."""
    approval_func = confidence_based_approval_func(reject_below=0.5, auto_approve_above=0.8)
    msg = Message(role="assistant", content="Response")
    request = ApprovalRequest(message=msg, confidence=0.3)

    response = approval_func(request)

    assert response.approved is False
    assert "Confidence too low" in response.feedback


def test_confidence_based_auto_approve():
    """Test confidence_based_approval_func auto-approval."""
    approval_func = confidence_based_approval_func(reject_below=0.5, auto_approve_above=0.8)
    msg = Message(role="assistant", content="Response")
    request = ApprovalRequest(message=msg, confidence=0.9)

    response = approval_func(request)

    assert response.approved is True
    assert "Auto-approved" in response.feedback


def test_confidence_based_middle_range():
    """Test confidence_based_approval_func in middle range."""
    approval_func = confidence_based_approval_func(reject_below=0.5, auto_approve_above=0.8)
    msg = Message(role="assistant", content="Response")
    request = ApprovalRequest(message=msg, confidence=0.7)

    response = approval_func(request)

    # Middle range requires manual approval (rejects by default)
    assert response.approved is False
    assert "Manual approval required" in response.feedback


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_workflow_high_confidence():
    """Test complete workflow with high confidence."""
    agent = MockAgent("agent", response="High confidence result", confidence=0.95)
    config = HumanInLoopConfig(
        agent=agent,
        approval_func=simple_approval_func(auto_approve=False),  # Would reject
        approval_threshold=0.8,
    )

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="Execute task")
    result = await hil.process(message)

    # Should bypass approval entirely
    assert result.content == "High confidence result"
    assert result.metadata["approval_status"] == "bypassed"


@pytest.mark.asyncio
async def test_full_workflow_low_confidence_approved():
    """Test complete workflow with low confidence and approval."""
    agent = MockAgent("agent", response="Low confidence result", confidence=0.6)
    config = HumanInLoopConfig(
        agent=agent, approval_func=simple_approval_func(auto_approve=True), approval_threshold=0.8
    )

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="Execute task")
    result = await hil.process(message)

    # Should go through approval and succeed
    assert result.content == "Low confidence result"
    assert result.metadata["approval_status"] == "approved"
    assert "Auto-approved" in result.metadata["approval_feedback"]


@pytest.mark.asyncio
async def test_full_workflow_confidence_based():
    """Test complete workflow with confidence-based approval function."""
    agent = MockAgent("agent", confidence=0.7)
    approval_func = confidence_based_approval_func(reject_below=0.5, auto_approve_above=0.8)
    config = HumanInLoopConfig(agent=agent, approval_func=approval_func, approval_threshold=0.8)

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="Execute task")
    result = await hil.process(message)

    # 0.7 is in middle range, should be rejected
    assert result.content == "Action rejected by human reviewer"
    assert result.metadata["approval_status"] == "rejected"


@pytest.mark.asyncio
async def test_reuse():
    """Test that HumanInLoopAgent can be reused."""
    agent = MockAgent("agent", confidence=0.95)
    config = HumanInLoopConfig(agent=agent, approval_func=always_approve)

    hil = HumanInLoopAgent(config)

    # First call
    message1 = Message(role="user", content="call1")
    await hil.process(message1)

    # Second call
    message2 = Message(role="user", content="call2")
    await hil.process(message2)

    # Agent should have been called twice
    assert agent.call_count == 2


# ============================================================================
# Async Approval Function Tests
# ============================================================================


async def async_always_approve(request: ApprovalRequest) -> ApprovalResponse:
    """Async version that always approves."""
    return ApprovalResponse(approved=True, feedback="Async approved")


async def async_always_reject(request: ApprovalRequest) -> ApprovalResponse:
    """Async version that always rejects."""
    return ApprovalResponse(approved=False, feedback="Async rejected")


async def async_modify_response(request: ApprovalRequest) -> ApprovalResponse:
    """Async version that approves with modifications."""
    modified = Message(role="assistant", content="Async modified response")
    return ApprovalResponse(approved=True, modified_message=modified, feedback="Modified async")


@pytest.mark.asyncio
async def test_async_approval_func_approve():
    """Test with async approval function that approves."""
    agent = MockAgent("agent", confidence=0.5)
    config = HumanInLoopConfig(
        agent=agent, approval_func=async_always_approve, approval_threshold=0.8
    )

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="Execute task")
    result = await hil.process(message)

    assert result.content == "Success"
    assert result.metadata["approval_status"] == "approved"
    assert result.metadata["approval_feedback"] == "Async approved"


@pytest.mark.asyncio
async def test_async_approval_func_reject():
    """Test with async approval function that rejects."""
    agent = MockAgent("agent", confidence=0.5)
    config = HumanInLoopConfig(
        agent=agent, approval_func=async_always_reject, approval_threshold=0.8
    )

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="Execute task")
    result = await hil.process(message)

    assert result.content == "Action rejected by human reviewer"
    assert result.metadata["approval_status"] == "rejected"
    assert result.metadata["rejection_reason"] == "Async rejected"


@pytest.mark.asyncio
async def test_async_approval_func_modify():
    """Test with async approval function that modifies response."""
    agent = MockAgent("agent", confidence=0.5)
    config = HumanInLoopConfig(
        agent=agent, approval_func=async_modify_response, approval_threshold=0.8
    )

    hil = HumanInLoopAgent(config)

    message = Message(role="user", content="Execute task")
    result = await hil.process(message)

    assert result.content == "Async modified response"
    assert result.metadata["approval_status"] == "approved_with_modifications"
    assert result.metadata["approval_feedback"] == "Modified async"
    assert result.metadata["original_response"] == "Success"


@pytest.mark.asyncio
async def test_mixed_sync_and_async_approval():
    """Test that both sync and async approval functions work."""
    agent_sync = MockAgent("sync_agent", confidence=0.5)
    agent_async = MockAgent("async_agent", confidence=0.5)

    config_sync = HumanInLoopConfig(
        agent=agent_sync, approval_func=always_approve, approval_threshold=0.8
    )
    config_async = HumanInLoopConfig(
        agent=agent_async, approval_func=async_always_approve, approval_threshold=0.8
    )

    hil_sync = HumanInLoopAgent(config_sync)
    hil_async = HumanInLoopAgent(config_async)

    message = Message(role="user", content="Execute task")

    result_sync = await hil_sync.process(message)
    result_async = await hil_async.process(message)

    # Both should approve
    assert result_sync.metadata["approval_status"] == "approved"
    assert result_async.metadata["approval_status"] == "approved"
