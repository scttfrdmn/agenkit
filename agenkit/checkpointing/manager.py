"""
Checkpoint manager for high-level checkpoint operations.

Provides operations like create, resume, replay, and time-travel debugging.
"""

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from .checkpoint import Checkpoint, CheckpointStorage
from .storage import MemoryCheckpointStorage

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manage checkpoints for long-running agents.

    Features:
    - Create checkpoints at key points
    - Resume from latest checkpoint
    - Replay from specific checkpoint
    - Time-travel debugging
    - Automatic checkpoint creation (every N steps)

    Example:
        >>> manager = CheckpointManager()
        >>>
        >>> # Create checkpoint
        >>> checkpoint_id = await manager.create_checkpoint(
        ...     session_id="session-1",
        ...     agent_name="assistant",
        ...     step_number=10,
        ...     state={"counter": 10, "mode": "active"},
        ...     messages=conversation_history
        ... )
        >>>
        >>> # Resume from latest
        >>> checkpoint = await manager.get_latest("session-1")
        >>> restored_state = checkpoint.state
    """

    def __init__(
        self, storage: CheckpointStorage | None = None, auto_checkpoint_interval: int | None = None
    ):
        """
        Initialize checkpoint manager.

        Args:
            storage: Checkpoint storage backend (defaults to in-memory)
            auto_checkpoint_interval: Automatically checkpoint every N steps (None = manual only)
        """
        self.storage = storage or MemoryCheckpointStorage()
        self.auto_checkpoint_interval = auto_checkpoint_interval

        # Track step counts for auto-checkpointing
        self._session_steps: dict[str, int] = {}
        self._session_last_checkpoint: dict[str, str] = {}

    async def create_checkpoint(
        self,
        session_id: str,
        agent_name: str,
        step_number: int,
        state: dict[str, Any],
        messages: list,
        metadata: dict[str, Any] | None = None,
        parent_checkpoint_id: str | None = None,
    ) -> str:
        """
        Create new checkpoint.

        Args:
            session_id: Session identifier
            agent_name: Agent name
            step_number: Sequential step number
            state: Agent state to save
            messages: Conversation messages
            metadata: Optional metadata
            parent_checkpoint_id: ID of previous checkpoint

        Returns:
            checkpoint_id: Unique identifier for this checkpoint

        Example:
            >>> checkpoint_id = await manager.create_checkpoint(
            ...     "session-1",
            ...     "assistant",
            ...     step_number=5,
            ...     state={"counter": 5},
            ...     messages=[msg1, msg2, msg3]
            ... )
        """
        checkpoint_id = str(uuid.uuid4())

        # Use last checkpoint as parent if not specified
        if parent_checkpoint_id is None:
            parent_checkpoint_id = self._session_last_checkpoint.get(session_id)

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            agent_name=agent_name,
            timestamp=datetime.now(UTC),
            step_number=step_number,
            state=state,
            messages=messages,
            metadata=metadata or {},
            parent_checkpoint_id=parent_checkpoint_id,
        )

        await self.storage.save(checkpoint)

        # Update tracking
        self._session_last_checkpoint[session_id] = checkpoint_id
        self._session_steps[session_id] = step_number

        logger.info(f"Created checkpoint {checkpoint_id} for {session_id} at step {step_number}")

        return checkpoint_id

    async def should_checkpoint(self, session_id: str, step_number: int) -> bool:
        """
        Determine if checkpoint should be created (for auto-checkpointing).

        Args:
            session_id: Session identifier
            step_number: Current step number

        Returns:
            True if checkpoint should be created
        """
        if self.auto_checkpoint_interval is None:
            return False

        last_step = self._session_steps.get(session_id, 0)
        steps_since_checkpoint = step_number - last_step

        return steps_since_checkpoint >= self.auto_checkpoint_interval

    async def get_latest(self, session_id: str) -> Checkpoint | None:
        """
        Get latest checkpoint for session.

        Args:
            session_id: Session identifier

        Returns:
            Latest checkpoint or None
        """
        return await self.storage.get_latest(session_id)

    async def load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """
        Load specific checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Checkpoint or None if not found
        """
        return await self.storage.load(checkpoint_id)

    async def list_checkpoints(self, session_id: str, limit: int | None = None) -> list[Checkpoint]:
        """
        List all checkpoints for session.

        Args:
            session_id: Session identifier
            limit: Optional limit on number of checkpoints

        Returns:
            List of checkpoints (most recent first)
        """
        return await self.storage.list_checkpoints(session_id, limit=limit)

    async def restore_state(self, checkpoint: Checkpoint) -> dict[str, Any]:
        """
        Restore agent state from checkpoint.

        Args:
            checkpoint: Checkpoint to restore from

        Returns:
            Restored state dictionary
        """
        logger.info(
            f"Restoring state from checkpoint {checkpoint.checkpoint_id} "
            f"(step {checkpoint.step_number})"
        )
        return checkpoint.state.copy()

    async def get_checkpoint_history(
        self, checkpoint_id: str, max_depth: int = 10
    ) -> list[Checkpoint]:
        """
        Get checkpoint history by following parent links.

        Args:
            checkpoint_id: Starting checkpoint
            max_depth: Maximum number of parents to follow

        Returns:
            List of checkpoints from most recent to oldest
        """
        return await self.storage.get_checkpoint_history(checkpoint_id, max_depth)

    async def replay_from_checkpoint(
        self,
        checkpoint_id: str,
        replay_fn: Callable[[Checkpoint, Any], Awaitable[Any]],
        up_to_step: int | None = None,
    ) -> list[Any]:
        """
        Replay execution from checkpoint.

        Args:
            checkpoint_id: Starting checkpoint
            replay_fn: Async function to execute for each step
                      Signature: async def replay_fn(checkpoint, state) -> result
            up_to_step: Optional step number to replay up to

        Returns:
            List of results from replay function

        Example:
            >>> async def replay_step(checkpoint, state):
            ...     print(f"Replaying step {checkpoint.step_number}")
            ...     return process_messages(checkpoint.messages)
            >>>
            >>> results = await manager.replay_from_checkpoint(
            ...     "checkpoint-id",
            ...     replay_fn=replay_step
            ... )
        """
        # Get checkpoint history
        history = await self.get_checkpoint_history(checkpoint_id)
        history.reverse()  # Oldest to newest

        results = []

        for checkpoint in history:
            # Stop if we've reached the target step
            if up_to_step and checkpoint.step_number > up_to_step:
                break

            # Execute replay function
            result = await replay_fn(checkpoint, checkpoint.state)
            results.append(result)

            logger.debug(f"Replayed step {checkpoint.step_number}")

        return results

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete specific checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            True if deleted, False if not found
        """
        return await self.storage.delete(checkpoint_id)

    async def delete_session(self, session_id: str) -> int:
        """
        Delete all checkpoints for session.

        Args:
            session_id: Session identifier

        Returns:
            Number of checkpoints deleted
        """
        count = await self.storage.delete_session(session_id)

        # Clean up tracking
        self._session_steps.pop(session_id, None)
        self._session_last_checkpoint.pop(session_id, None)

        return count

    async def get_session_stats(self, session_id: str) -> dict:
        """
        Get statistics for session checkpoints.

        Args:
            session_id: Session identifier

        Returns:
            Dict with statistics
        """
        checkpoints = await self.list_checkpoints(session_id)

        if not checkpoints:
            return {
                "total_checkpoints": 0,
                "first_checkpoint": None,
                "latest_checkpoint": None,
                "steps_covered": 0,
            }

        return {
            "total_checkpoints": len(checkpoints),
            "first_checkpoint": checkpoints[-1].checkpoint_id,
            "latest_checkpoint": checkpoints[0].checkpoint_id,
            "first_step": checkpoints[-1].step_number,
            "latest_step": checkpoints[0].step_number,
            "steps_covered": checkpoints[0].step_number - checkpoints[-1].step_number,
            "time_span": (checkpoints[0].timestamp - checkpoints[-1].timestamp).total_seconds(),
        }

    async def prune_old_checkpoints(self, session_id: str, keep_last: int = 10) -> int:
        """
        Prune old checkpoints, keeping only the most recent N.

        Args:
            session_id: Session identifier
            keep_last: Number of most recent checkpoints to keep

        Returns:
            Number of checkpoints deleted

        Example:
            >>> # Keep only last 10 checkpoints
            >>> deleted = await manager.prune_old_checkpoints("session-1", keep_last=10)
            >>> print(f"Deleted {deleted} old checkpoints")
        """
        checkpoints = await self.list_checkpoints(session_id)

        if len(checkpoints) <= keep_last:
            return 0

        # Delete old checkpoints
        to_delete = checkpoints[keep_last:]
        deleted_count = 0

        for checkpoint in to_delete:
            if await self.storage.delete(checkpoint.checkpoint_id):
                deleted_count += 1

        logger.info(
            f"Pruned {deleted_count} old checkpoints for {session_id}, kept {keep_last} most recent"
        )

        return deleted_count
