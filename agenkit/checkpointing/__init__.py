"""
Checkpointing and durable execution for long-running agents.

This package provides checkpointing capabilities for 30-hour autonomous agents,
enabling state persistence, crash recovery, and time-travel debugging.

Classes:
    Checkpoint: Checkpoint data structure
    CheckpointStorage: Abstract storage interface
    InMemoryCheckpointStorage: In-memory storage (testing)
    FileCheckpointStorage: File-based storage (production)
    CheckpointManager: High-level checkpoint management
    DurableAgent: Agent wrapper with automatic checkpointing

Example:
    >>> from agenkit.checkpointing import DurableAgent
    >>>
    >>> # Make agent durable
    >>> durable = DurableAgent(
    ...     agent=my_agent,
    ...     checkpoint_dir="./checkpoints",
    ...     checkpoint_interval=10
    ... )
    >>>
    >>> # Use agent (auto-checkpoints every 10 steps)
    >>> response = await durable.process(message, session_id="session-1")
    >>>
    >>> # Resume from checkpoint after restart
    >>> state = await durable.resume("session-1")
"""

from .checkpoint import Checkpoint, CheckpointStorage
from .durable import DurableAgent, make_durable
from .manager import CheckpointManager
from .storage import FileCheckpointStorage, InMemoryCheckpointStorage

__all__ = [
    # Core
    "Checkpoint",
    # Management
    "CheckpointManager",
    "CheckpointStorage",
    # Durable execution
    "DurableAgent",
    "FileCheckpointStorage",
    # Storage
    "InMemoryCheckpointStorage",
    "make_durable",
]
