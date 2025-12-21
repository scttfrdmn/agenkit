"""
Human-in-Loop Agent Pattern

Human-in-Loop pattern implements agent execution with human approval
for high-stakes decisions. When agent confidence is below a threshold,
human approval is requested before proceeding.

Key concepts:
- Confidence-based approval gates
- Human oversight for critical decisions
- Configurable approval thresholds
- Callback-based approval mechanism

Performance characteristics:
- Time: O(agent) + human response time (when approval needed)
- Memory: O(1) for message passing
- Blocking on human input when required
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from agenkit import Agent, Message


@dataclass
class ApprovalRequest:
    """
    Contains information about a pending approval decision.

    Attributes:
        message: The agent's proposed response
        confidence: Agent's confidence level (0.0 to 1.0)
        context: Additional decision context
        timestamp: When approval was requested
    """

    message: Message
    confidence: float
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())


@dataclass
class ApprovalResponse:
    """
    Represents the human's decision.

    Attributes:
        approved: Whether the action is approved
        feedback: Optional human feedback
        modified_message: Optional modified version (if approved with changes)
    """

    approved: bool
    feedback: str = ""
    modified_message: Message | None = None


# Type alias for approval callback function
ApprovalFunc = Callable[[ApprovalRequest], ApprovalResponse]


@dataclass
class HumanInLoopConfig:
    """
    Configuration for a HumanInLoopAgent.

    Attributes:
        agent: Agent to wrap with human approval
        approval_threshold: Threshold for requiring approval (0.0 to 1.0, default: 0.8)
                           Responses with confidence below this require approval
        approval_func: Called when approval is needed
        confidence_key: Metadata key for confidence (default: "confidence")
    """

    agent: Agent
    approval_func: ApprovalFunc
    approval_threshold: float = 0.8
    confidence_key: str = "confidence"


class HumanInLoopAgent(Agent):
    """
    Wraps an agent with human approval gates.

    The agent executes normally, but when confidence is below the threshold,
    human approval is requested before returning the response. This provides
    oversight for high-stakes decisions while allowing autonomous operation
    for routine tasks.

    Example use cases:
    - Financial trading: approve large transactions
    - Content moderation: verify edge cases
    - Healthcare: approve treatment recommendations
    - Legal: review contract changes
    - Security: approve access grants

    The human-in-loop pattern is ideal when autonomous operation needs
    human oversight for critical or uncertain decisions.

    Example:
        ```python
        from agenkit.patterns import HumanInLoopAgent, HumanInLoopConfig

        def approval_handler(request: ApprovalRequest) -> ApprovalResponse:
            print(f"Approve? Confidence: {request.confidence}")
            print(f"Message: {request.message.content}")
            response = input("Approve (y/n)? ")
            return ApprovalResponse(approved=response.lower() == "y")

        config = HumanInLoopConfig(
            agent=trading_agent,
            approval_threshold=0.8,
            approval_func=approval_handler
        )

        agent = HumanInLoopAgent(config)
        result = await agent.process(
            Message(role="user", content="Execute this trade")
        )
        ```
    """

    def __init__(self, config: HumanInLoopConfig) -> None:
        """
        Create a new human-in-loop agent.

        Args:
            config: Configuration with agent and approval settings

        Raises:
            ValueError: If config is None, agent is None, approval_func is None,
                       or approval_threshold is invalid

        The approval threshold determines when human approval is required.
        A threshold of 0.8 means approval is needed when confidence < 0.8.
        The agent's response metadata should include a confidence value.
        """
        if config is None:
            raise ValueError("config is required")
        if config.agent is None:
            raise ValueError("agent is required")
        if config.approval_func is None:
            raise ValueError("approval function is required")

        threshold = config.approval_threshold
        if threshold < 0 or threshold > 1:
            raise ValueError(
                f"approval threshold must be between 0 and 1 (got {threshold:.2f})"
            )

        confidence_key = config.confidence_key or "confidence"

        self._agent = config.agent
        self._approval_threshold = threshold
        self._approval_func = config.approval_func
        self._confidence_key = confidence_key

    @property
    def name(self) -> str:
        """Return the agent's identifier."""
        return "HumanInLoopAgent"

    def capabilities(self) -> list[str]:
        """Return the agent's capabilities plus human-in-loop."""
        caps = self._agent.capabilities()
        return [*caps, "human-in-loop", "approval", "oversight"]

    async def process(self, message: Message) -> Message:
        """
        Execute the agent with human approval when needed.

        The process follows these steps:
        1. Execute underlying agent
        2. Extract confidence from response metadata
        3. If confidence < threshold, request human approval
        4. Return approved response or rejection message

        If approval is denied, a message indicating rejection is returned.
        If approval includes modifications, the modified message is returned.

        The final message includes metadata about the approval process.

        Args:
            message: Input message to process

        Returns:
            Approved response or rejection message

        Raises:
            ValueError: If message is None
            RuntimeError: If agent execution or approval request fails
        """
        if message is None:
            raise ValueError("message cannot be None")

        # Execute underlying agent
        try:
            response = await self._agent.process(message)
        except Exception as e:
            raise RuntimeError(f"agent execution failed: {e}") from e

        # Extract confidence from metadata
        confidence = self._extract_confidence(response)

        # Check if approval needed
        needs_approval = confidence < self._approval_threshold

        # Add approval metadata
        if response.metadata is None:
            response.metadata = {}
        response.metadata["approval_needed"] = needs_approval
        response.metadata["confidence"] = confidence
        response.metadata["approval_threshold"] = self._approval_threshold

        # Add escalation metadata (alias for approval_needed)
        if needs_approval:
            response.metadata["escalated"] = True
            response.metadata["escalation_reason"] = "low_confidence"

        # If high confidence, return without approval
        if not needs_approval:
            response.metadata["approval_status"] = "bypassed"
            return response

        # Request human approval
        request = ApprovalRequest(
            message=response,
            confidence=confidence,
            context={
                "agent": self._agent.name,
                "approval_threshold": self._approval_threshold,
                "original_message": message.content,
                "confidence_shortfall": self._approval_threshold - confidence,
            },
        )

        try:
            approval = self._approval_func(request)
        except Exception as e:
            raise RuntimeError(f"approval request failed: {e}") from e

        # Handle approval decision
        if not approval.approved:
            # Request denied
            rejection_msg = Message(
                role="agent",
                content="Action rejected by human reviewer",
            )

            if approval.feedback:
                rejection_msg.metadata = {"rejection_reason": approval.feedback}
            else:
                rejection_msg.metadata = {}

            rejection_msg.metadata["approval_status"] = "rejected"
            rejection_msg.metadata["original_response"] = response.content
            rejection_msg.metadata["confidence"] = confidence

            return rejection_msg

        # Request approved
        final_response = response
        if approval.modified_message is not None:
            # Use modified version
            final_response = approval.modified_message
            if final_response.metadata is None:
                final_response.metadata = {}
            final_response.metadata["approval_status"] = "approved_with_modifications"
            final_response.metadata["original_response"] = response.content
        else:
            final_response.metadata["approval_status"] = "approved"

        if approval.feedback:
            final_response.metadata["approval_feedback"] = approval.feedback

        return final_response

    def _extract_confidence(self, message: Message) -> float:
        """Get confidence value from message metadata."""
        if message.metadata is None:
            return 0.0

        confidence_val = message.metadata.get(self._confidence_key)
        if confidence_val is None:
            return 0.0

        # Try to convert to float
        try:
            return float(confidence_val)
        except (ValueError, TypeError):
            return 0.0


def simple_approval_func(auto_approve: bool) -> ApprovalFunc:
    """
    Create a basic approval function for testing/demos.

    This function automatically approves or rejects based on a static decision.
    For production use, implement a custom ApprovalFunc that prompts humans.

    Args:
        auto_approve: Whether to automatically approve all requests

    Returns:
        Approval function with configured behavior

    Example:
        ```python
        # Auto-approve all requests
        approval_func = simple_approval_func(auto_approve=True)

        # Auto-reject all requests
        approval_func = simple_approval_func(auto_approve=False)
        ```
    """
    def approve(request: ApprovalRequest) -> ApprovalResponse:
        status = "approved" if auto_approve else "rejected"
        return ApprovalResponse(
            approved=auto_approve,
            feedback=f"Auto-{status} (confidence: {request.confidence:.2f})",
        )

    return approve


def confidence_based_approval_func(
    reject_below: float, auto_approve_above: float
) -> ApprovalFunc:
    """
    Create an approval function with dynamic thresholds.

    This allows different approval rules based on confidence levels. For example:
    - Very low confidence (< 0.5): always reject
    - Low confidence (0.5-0.7): require approval
    - Medium confidence (0.7-0.8): require approval
    - High confidence (>= 0.8): auto-approve

    Args:
        reject_below: Confidence threshold for automatic rejection
        auto_approve_above: Confidence threshold for automatic approval

    Returns:
        Approval function with configured thresholds

    Example:
        ```python
        # Auto-reject below 0.5, auto-approve above 0.8
        approval_func = confidence_based_approval_func(
            reject_below=0.5,
            auto_approve_above=0.8
        )
        ```
    """
    def approve(request: ApprovalRequest) -> ApprovalResponse:
        conf = request.confidence

        if conf < reject_below:
            return ApprovalResponse(
                approved=False,
                feedback=f"Confidence too low ({conf:.2f} < {reject_below:.2f})",
            )

        if conf >= auto_approve_above:
            return ApprovalResponse(
                approved=True,
                feedback=f"Auto-approved ({conf:.2f} >= {auto_approve_above:.2f})",
            )

        # In this range, you would typically prompt a human
        # For this example, we'll reject to be safe
        return ApprovalResponse(
            approved=False,
            feedback=f"Manual approval required ({conf:.2f} in threshold range)",
        )

    return approve
