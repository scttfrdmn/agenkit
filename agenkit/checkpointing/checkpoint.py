"""
Checkpoint data structures and storage interface.

Checkpoints capture agent state at a point in time, enabling:
- Resume after crashes/restarts
- Time-travel debugging
- Durable execution for long-running agents
"""

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Checkpoint:
    """
    Checkpoint capturing agent state at a point in time.

    Attributes:
        checkpoint_id: Unique checkpoint identifier
        session_id: Session this checkpoint belongs to
        agent_name: Name of the agent
        timestamp: When checkpoint was created
        step_number: Sequential step number in session
        state: Agent state (custom data)
        messages: Conversation messages up to this point
        metadata: Additional metadata (cost, tokens, etc.)
        parent_checkpoint_id: ID of previous checkpoint (for history)
    """

    checkpoint_id: str
    session_id: str
    agent_name: str
    timestamp: datetime
    step_number: int
    state: dict[str, Any]
    messages: list
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_checkpoint_id: str | None = None

    def to_dict(self) -> dict:
        """Convert checkpoint to dictionary for serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()

        # Serialize messages (convert datetime timestamps to ISO format)
        serialized_messages = []
        for msg in self.messages:
            if hasattr(msg, "__dict__"):
                msg_dict = msg.__dict__.copy() if hasattr(msg, "__dict__") else asdict(msg)
                if "timestamp" in msg_dict and hasattr(msg_dict["timestamp"], "isoformat"):
                    msg_dict["timestamp"] = msg_dict["timestamp"].isoformat()
                serialized_messages.append(msg_dict)
            else:
                serialized_messages.append(msg)
        data["messages"] = serialized_messages

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        """Create checkpoint from dictionary."""
        from ..interfaces import Message

        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        # Deserialize messages (convert ISO timestamps back to datetime)
        deserialized_messages = []
        for msg in data.get("messages", []):
            if isinstance(msg, dict):
                msg = msg.copy()
                if "timestamp" in msg and isinstance(msg["timestamp"], str):
                    msg["timestamp"] = datetime.fromisoformat(msg["timestamp"])
                deserialized_messages.append(Message(**msg))
            else:
                deserialized_messages.append(msg)
        data["messages"] = deserialized_messages

        return cls(**data)

    def to_json(self) -> str:
        """Serialize checkpoint to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Checkpoint":
        """Deserialize checkpoint from JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class CheckpointStorage(ABC):
    """
    Abstract interface for checkpoint storage backends.

    Implementations:
    - InMemoryCheckpointStorage: For testing/development
    - FileCheckpointStorage: For persistence to disk
    - RedisCheckpointStorage: For distributed systems
    """

    @abstractmethod
    async def save(self, checkpoint: Checkpoint) -> None:
        """
        Save checkpoint to storage.

        Args:
            checkpoint: Checkpoint to save
        """
        pass

    @abstractmethod
    async def load(self, checkpoint_id: str) -> Checkpoint | None:
        """
        Load checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Checkpoint if found, None otherwise
        """
        pass

    @abstractmethod
    async def list_checkpoints(self, session_id: str, limit: int | None = None) -> list[Checkpoint]:
        """
        List checkpoints for session.

        Args:
            session_id: Session identifier
            limit: Optional limit on number of checkpoints

        Returns:
            List of checkpoints (most recent first)
        """
        pass

    @abstractmethod
    async def get_latest(self, session_id: str) -> Checkpoint | None:
        """
        Get latest checkpoint for session.

        Args:
            session_id: Session identifier

        Returns:
            Latest checkpoint if exists, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, checkpoint_id: str) -> bool:
        """
        Delete checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> int:
        """
        Delete all checkpoints for session.

        Args:
            session_id: Session identifier

        Returns:
            Number of checkpoints deleted
        """
        pass

    @abstractmethod
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
        pass
