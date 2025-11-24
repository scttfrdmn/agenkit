"""
Durable agent wrapper for automatic checkpointing.

Wraps agents to provide automatic checkpointing, resume, and error recovery.
"""

import logging
from typing import Any

from ..interfaces import Agent, Message
from .manager import CheckpointManager
from .storage import FileCheckpointStorage

logger = logging.getLogger(__name__)


class DurableAgent:
    """
    Wrap agent with automatic checkpointing and resume capability.

    Features:
    - Automatic checkpointing (every N steps or on demand)
    - Resume from latest checkpoint on startup
    - State persistence across restarts
    - Error recovery with checkpoint rollback

    Example:
        >>> from agenkit.checkpointing import DurableAgent, FileCheckpointStorage
        >>>
        >>> # Create durable agent
        >>> storage = FileCheckpointStorage("./checkpoints")
        >>> durable = DurableAgent(
        ...     agent=my_agent,
        ...     checkpoint_dir="./checkpoints",
        ...     checkpoint_interval=10  # Every 10 steps
        ... )
        >>>
        >>> # Use agent (automatically checkpoints)
        >>> response = await durable.process(message, session_id="session-1")
        >>>
        >>> # Resume from checkpoint
        >>> state = await durable.resume("session-1")
    """

    def __init__(
        self,
        agent: Agent,
        checkpoint_dir: str | None = None,
        checkpoint_interval: int = 10,
        auto_resume: bool = True,
        agent_name: str | None = None,
    ):
        """
        Initialize durable agent.

        Args:
            agent: Agent to wrap
            checkpoint_dir: Directory for checkpoints (None = in-memory)
            checkpoint_interval: Checkpoint every N steps
            auto_resume: Automatically resume from latest checkpoint on first call
            agent_name: Override agent name (defaults to agent.name)
        """
        self.agent = agent
        self.agent_name = agent_name or getattr(agent, "name", "agent")
        self.checkpoint_interval = checkpoint_interval
        self.auto_resume = auto_resume

        # Initialize checkpoint manager
        if checkpoint_dir:
            storage = FileCheckpointStorage(checkpoint_dir)
            self.manager = CheckpointManager(
                storage=storage, auto_checkpoint_interval=checkpoint_interval
            )
        else:
            self.manager = CheckpointManager(auto_checkpoint_interval=checkpoint_interval)

        # Track state per session
        self._session_state: dict[str, dict[str, Any]] = {}
        self._session_steps: dict[str, int] = {}
        self._session_messages: dict[str, list] = {}
        self._session_resumed: dict[str, bool] = {}

    async def process(self, message: Message, session_id: str = "default", **kwargs) -> Message:
        """
        Process message with automatic checkpointing.

        Args:
            message: Input message
            session_id: Session identifier
            **kwargs: Additional arguments for agent

        Returns:
            Response message
        """
        # Auto-resume on first call if enabled
        if self.auto_resume and not self._session_resumed.get(session_id, False):
            await self.resume(session_id)
            self._session_resumed[session_id] = True

        # Initialize session if needed
        if session_id not in self._session_state:
            self._session_state[session_id] = {}
            self._session_steps[session_id] = 0
            self._session_messages[session_id] = []

        # Increment step
        self._session_steps[session_id] += 1
        current_step = self._session_steps[session_id]

        # Add message to history
        self._session_messages[session_id].append(message)

        try:
            # Process message
            response = await self.agent.process(message)

            # Add response to history
            self._session_messages[session_id].append(response)

            # Update state
            self._update_state(session_id, message, response)

            # Checkpoint if needed
            if await self.manager.should_checkpoint(session_id, current_step):
                await self.checkpoint(session_id)

            return response

        except Exception as e:
            logger.error(f"Error processing message at step {current_step}: {e}")

            # Try to rollback to last checkpoint
            latest = await self.manager.get_latest(session_id)
            if latest:
                logger.info(f"Rolling back to checkpoint at step {latest.step_number}")
                await self.resume(session_id, checkpoint_id=latest.checkpoint_id)

            raise

    async def checkpoint(self, session_id: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Create checkpoint for current state.

        Args:
            session_id: Session identifier
            metadata: Optional metadata to attach

        Returns:
            checkpoint_id: Unique checkpoint identifier
        """
        current_step = self._session_steps.get(session_id, 0)
        state = self._session_state.get(session_id, {})
        messages = self._session_messages.get(session_id, [])

        checkpoint_id = await self.manager.create_checkpoint(
            session_id=session_id,
            agent_name=self.agent_name,
            step_number=current_step,
            state=state,
            messages=messages,
            metadata=metadata,
        )

        logger.info(f"Checkpointed session {session_id} at step {current_step}")

        return checkpoint_id

    async def resume(
        self, session_id: str, checkpoint_id: str | None = None
    ) -> dict[str, Any] | None:
        """
        Resume from checkpoint.

        Args:
            session_id: Session identifier
            checkpoint_id: Specific checkpoint to resume from (None = latest)

        Returns:
            Restored state or None if no checkpoint found
        """
        # Load checkpoint
        if checkpoint_id:
            checkpoint = await self.manager.load_checkpoint(checkpoint_id)
        else:
            checkpoint = await self.manager.get_latest(session_id)

        if not checkpoint:
            logger.info(f"No checkpoint found for {session_id}, starting fresh")
            return None

        # Restore state
        self._session_state[session_id] = checkpoint.state.copy()
        self._session_steps[session_id] = checkpoint.step_number
        self._session_messages[session_id] = checkpoint.messages.copy()

        logger.info(
            f"Resumed session {session_id} from checkpoint at step {checkpoint.step_number}"
        )

        return checkpoint.state

    async def get_state(self, session_id: str) -> dict[str, Any]:
        """Get current state for session."""
        return self._session_state.get(session_id, {}).copy()

    async def set_state(self, session_id: str, state: dict[str, Any]) -> None:
        """Set state for session."""
        self._session_state[session_id] = state.copy()

    async def get_messages(self, session_id: str) -> list:
        """Get message history for session."""
        return self._session_messages.get(session_id, []).copy()

    async def reset_session(self, session_id: str) -> None:
        """Reset session (clear state and messages)."""
        self._session_state.pop(session_id, None)
        self._session_steps.pop(session_id, None)
        self._session_messages.pop(session_id, None)
        self._session_resumed.pop(session_id, None)

    def _update_state(
        self, session_id: str, input_message: Message, output_message: Message
    ) -> None:
        """
        Update session state (can be overridden for custom state tracking).

        Default implementation tracks message count and last message.
        Override this to track custom state.
        """
        state = self._session_state[session_id]

        # Update basic stats
        state["message_count"] = state.get("message_count", 0) + 1
        state["last_input"] = input_message.content
        state["last_output"] = output_message.content

        # Track any metadata from response
        if hasattr(output_message, "metadata") and output_message.metadata:
            state["last_metadata"] = output_message.metadata

    async def list_checkpoints(self, session_id: str, limit: int | None = None) -> list:
        """List checkpoints for session."""
        return await self.manager.list_checkpoints(session_id, limit=limit)

    async def delete_checkpoints(self, session_id: str) -> int:
        """Delete all checkpoints for session."""
        count = await self.manager.delete_session(session_id)
        await self.reset_session(session_id)
        return count

    async def get_session_stats(self, session_id: str) -> dict:
        """Get statistics for session."""
        checkpoint_stats = await self.manager.get_session_stats(session_id)

        return {
            **checkpoint_stats,
            "current_step": self._session_steps.get(session_id, 0),
            "message_count": len(self._session_messages.get(session_id, [])),
            "state_size": len(self._session_state.get(session_id, {})),
        }


def make_durable(
    agent: Agent,
    checkpoint_dir: str = "./checkpoints",
    checkpoint_interval: int = 10,
    agent_name: str | None = None,
) -> DurableAgent:
    """
    Convenience function to make an agent durable.

    Args:
        agent: Agent to make durable
        checkpoint_dir: Directory for checkpoints
        checkpoint_interval: Checkpoint every N steps
        agent_name: Override agent name

    Returns:
        DurableAgent wrapping the original agent

    Example:
        >>> from agenkit.checkpointing import make_durable
        >>>
        >>> # Make agent durable
        >>> durable_agent = make_durable(
        ...     my_agent,
        ...     checkpoint_dir="./checkpoints",
        ...     checkpoint_interval=5
        ... )
        >>>
        >>> # Use like normal agent
        >>> response = await durable_agent.process(message, session_id="session-1")
    """
    return DurableAgent(
        agent=agent,
        checkpoint_dir=checkpoint_dir,
        checkpoint_interval=checkpoint_interval,
        agent_name=agent_name,
    )
