"""MiniCopilotKit - CopilotKit patterns reimagined on Agenkit.

This module demonstrates how to implement CopilotKit-like patterns using
Agenkit's AG-UI Standard protocol, showing that CopilotKit's features are
built on the same primitives that Agenkit provides.

Key Patterns Demonstrated:
1. Streaming Chat UI (like <CopilotChat>)
2. Tool Visualization (like CopilotKit's tool cards)
3. HITL Approval (like useConfirmation)
4. Shared State (like useCopilotReadable/useCopilotAction)
5. Real-time Updates (like CopilotKit's reactive state)

Architecture:
- CopilotAgent: Base agent with CopilotKit-style features
- ChatUI: Streaming chat interface with tool visualization
- StateHook: Shared state management (frontend ↔ backend)
- ApprovalDialog: HITL confirmation workflows
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Optional

from agenkit import Agent, Message
from agenkit.protocols.agui import (
    AGUIAdapter,
    Event,
    StateManager,
    ToolCallTracker,
)


# ============================================
# Core Abstractions
# ============================================


@dataclass
class StateHook:
    """Shared state hook (like useCopilotReadable/useCopilotAction).

    Implements bidirectional state synchronization between agent and frontend,
    similar to CopilotKit's hooks but using AG-UI StateManager.

    Example:
        >>> hook = StateHook("counter", initial_value=0)
        >>> hook.update(5)  # Update from agent
        >>> hook.get()      # Get current value
        5
    """

    name: str
    initial_value: Any = None
    _state_manager: Optional[StateManager] = None
    _path: str = field(init=False)

    def __post_init__(self):
        """Initialize state path."""
        self._path = f"/hooks/{self.name}"
        if self._state_manager is None:
            # Create isolated state manager for this hook
            self._state_manager = StateManager(
                initial_state={"hooks": {self.name: self.initial_value}}
            )

    def get(self) -> Any:
        """Get current value.

        Returns:
            Current hook value
        """
        state = self._state_manager.get_state()
        return state.get("hooks", {}).get(self.name)

    def update(self, value: Any) -> None:
        """Update value (agent → frontend).

        Args:
            value: New value
        """
        self._state_manager.update(self._path, value)

    def get_delta_event(self):
        """Get StateDelta event for transmission to frontend.

        Returns:
            StateDelta event or None if no changes
        """
        return self._state_manager.get_delta_event()


@dataclass
class ApprovalDialog:
    """HITL approval dialog (like useConfirmation).

    Implements human-in-the-loop approval workflows, similar to CopilotKit's
    confirmation dialogs but using AG-UI interrupt events.

    Example:
        >>> dialog = ApprovalDialog(
        ...     title="Confirm Action",
        ...     message="Delete 10 files?",
        ...     options=["Approve", "Reject", "Modify"]
        ... )
        >>> response = await dialog.request_approval()
        >>> if response == "Approve":
        ...     # Proceed with action
    """

    title: str
    message: str
    options: list[str] = field(default_factory=lambda: ["Approve", "Reject"])
    severity: str = "info"  # info, warning, error

    async def request_approval(self) -> str:
        """Request approval from user.

        Returns:
            User's response (one of options)

        Note:
            In a real implementation, this would emit an AG-UI interrupt
            event and wait for user response. For this example, we simulate.
        """
        # In real implementation:
        # 1. Emit interrupt event with dialog data
        # 2. Wait for interrupt_response event
        # 3. Return user's choice
        await asyncio.sleep(0.1)  # Simulate wait
        return self.options[0]  # Simulate approval


@dataclass
class ToolCard:
    """Tool execution visualization (like CopilotKit's tool cards).

    Provides rich UI representation of tool calls, similar to CopilotKit's
    tool visualization but using AG-UI tool call events.

    Example:
        >>> card = ToolCard(
        ...     tool_name="search",
        ...     status="executing",
        ...     progress=0.5
        ... )
    """

    tool_name: str
    tool_call_id: str
    status: str = "pending"  # pending, executing, completed, failed
    progress: float = 0.0  # 0.0 to 1.0
    args: Optional[dict] = None
    result: Optional[Any] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for frontend.

        Returns:
            Tool card data
        """
        return {
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "status": self.status,
            "progress": self.progress,
            "args": self.args,
            "result": self.result,
        }


# ============================================
# CopilotAgent - Agent with CopilotKit Features
# ============================================


class CopilotAgent:
    """Base agent with CopilotKit-style features.

    Wraps an Agenkit agent to provide CopilotKit-like capabilities:
    - Streaming chat UI
    - Tool visualization
    - HITL approvals
    - Shared state hooks

    Example:
        >>> agent = CopilotAgent(
        ...     base_agent=MyAgent(),
        ...     tools=[SearchTool(), CalculatorTool()],
        ...     hooks=[StateHook("counter", 0)]
        ... )
        >>> async for event in agent.stream_chat(message):
        ...     # Handle streaming events
    """

    def __init__(
        self,
        base_agent: Agent,
        tools: Optional[list] = None,
        hooks: Optional[list[StateHook]] = None,
        enable_approvals: bool = True,
    ):
        """Initialize CopilotAgent.

        Args:
            base_agent: Underlying Agenkit agent
            tools: List of tools for visualization
            hooks: List of state hooks
            enable_approvals: Enable HITL approvals
        """
        self.base_agent = base_agent
        self.tools = tools or []
        self.hooks = {hook.name: hook for hook in (hooks or [])}
        self.enable_approvals = enable_approvals

        # Create state manager combining all hook states
        hook_states = {hook.name: hook.initial_value for hook in (hooks or [])}
        self.state_manager = StateManager(initial_state={"hooks": hook_states})

        # Update hooks to use shared state manager
        for hook in self.hooks.values():
            hook._state_manager = self.state_manager

        # Create adapter
        self.adapter = AGUIAdapter(
            base_agent,
            state_manager=self.state_manager,
            emit_state_snapshots=True,
        )

        # Tool call tracker
        self.tool_tracker = ToolCallTracker()

        # Active tool cards
        self.active_tools: dict[str, ToolCard] = {}

    async def stream_chat(
        self,
        message: Message,
        thread_id: str = "default",
    ) -> AsyncIterator[Event]:
        """Stream chat events with CopilotKit features.

        Args:
            message: User message
            thread_id: Conversation thread ID

        Yields:
            AG-UI events for frontend consumption
        """
        # Stream events from adapter
        async for event in self.adapter.stream_events(message, thread_id):
            # Track tool calls for visualization
            if event.type == "tool_call_start":
                self.active_tools[event.tool_call_id] = ToolCard(
                    tool_name=event.tool_call_name,
                    tool_call_id=event.tool_call_id,
                    status="executing",
                )

            elif event.type == "tool_call_progress":
                if event.tool_call_id in self.active_tools:
                    card = self.active_tools[event.tool_call_id]
                    card.progress = event.progress
                    card.status = "executing"

            elif event.type == "tool_call_result":
                if event.tool_call_id in self.active_tools:
                    card = self.active_tools[event.tool_call_id]
                    card.status = "completed"
                    card.result = event.content

            yield event

    def get_hook(self, name: str) -> Optional[StateHook]:
        """Get state hook by name.

        Args:
            name: Hook name

        Returns:
            StateHook or None
        """
        return self.hooks.get(name)

    def get_active_tools(self) -> list[dict]:
        """Get active tool cards for UI.

        Returns:
            List of tool card dictionaries
        """
        return [card.to_dict() for card in self.active_tools.values()]


# ============================================
# ChatUI - Streaming Chat Interface
# ============================================


class ChatUI:
    """Streaming chat UI (like <CopilotChat>).

    Provides a simple text-based chat interface that demonstrates the
    streaming chat pattern, similar to CopilotKit's CopilotChat component.

    Example:
        >>> ui = ChatUI(agent)
        >>> await ui.send_message("Hello!")
        >>> await ui.display_chat()
    """

    def __init__(self, agent: CopilotAgent):
        """Initialize chat UI.

        Args:
            agent: CopilotAgent instance
        """
        self.agent = agent
        self.messages: list[dict] = []
        self.thread_id = "chat-session"

    async def send_message(self, content: str) -> str:
        """Send message and get streaming response.

        Args:
            content: User message content

        Returns:
            Complete assistant response
        """
        # Add user message
        self.messages.append({"role": "user", "content": content})

        # Stream response
        message = Message(role="user", content=content)
        response_parts = []

        async for event in self.agent.stream_chat(message, self.thread_id):
            if event.type == "text_message_content":
                response_parts.append(event.delta)

        response = "".join(response_parts)
        self.messages.append({"role": "assistant", "content": response})

        return response

    def display_chat(self) -> str:
        """Display chat history (simple text format).

        Returns:
            Formatted chat history
        """
        lines = []
        for msg in self.messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)


# ============================================
# Helper Functions
# ============================================


def create_copilot_agent(
    agent: Agent,
    initial_state: Optional[dict[str, Any]] = None,
) -> CopilotAgent:
    """Create a CopilotAgent with default configuration.

    Args:
        agent: Base Agenkit agent
        initial_state: Initial state for hooks

    Returns:
        Configured CopilotAgent

    Example:
        >>> agent = create_copilot_agent(
        ...     MyAgent(),
        ...     initial_state={"counter": 0, "todos": []}
        ... )
    """
    hooks = []
    if initial_state:
        for name, value in initial_state.items():
            hooks.append(StateHook(name, value))

    return CopilotAgent(agent, hooks=hooks)


__all__ = [
    "CopilotAgent",
    "StateHook",
    "ApprovalDialog",
    "ToolCard",
    "ChatUI",
    "create_copilot_agent",
]
