"""
Tests for checkpoint core functionality and storage.
"""

import shutil
import tempfile
from datetime import datetime, timezone

import pytest

from agenkit.checkpointing import (
    Checkpoint,
    CheckpointManager,
    FileCheckpointStorage,
    InMemoryCheckpointStorage,
)
from agenkit.interfaces import Message

# ===== Checkpoint Tests =====


def test_checkpoint_creation():
    """Test creating a checkpoint."""
    checkpoint = Checkpoint(
        checkpoint_id="checkpoint-1",
        session_id="session-1",
        agent_name="assistant",
        timestamp=datetime.now(timezone.utc),
        step_number=10,
        state={"counter": 10, "mode": "active"},
        messages=[Message(role="user", content="Hello")],
        metadata={"cost": 0.05},
    )

    assert checkpoint.checkpoint_id == "checkpoint-1"
    assert checkpoint.session_id == "session-1"
    assert checkpoint.step_number == 10
    assert checkpoint.state["counter"] == 10


def test_checkpoint_to_dict():
    """Test converting checkpoint to dictionary."""
    checkpoint = Checkpoint(
        checkpoint_id="checkpoint-1",
        session_id="session-1",
        agent_name="assistant",
        timestamp=datetime.now(timezone.utc),
        step_number=10,
        state={"counter": 10},
        messages=[],
        metadata={},
    )

    checkpoint_dict = checkpoint.to_dict()

    assert checkpoint_dict["checkpoint_id"] == "checkpoint-1"
    assert checkpoint_dict["session_id"] == "session-1"
    assert isinstance(checkpoint_dict["timestamp"], str)


def test_checkpoint_from_dict():
    """Test creating checkpoint from dictionary."""
    data = {
        "checkpoint_id": "checkpoint-1",
        "session_id": "session-1",
        "agent_name": "assistant",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step_number": 10,
        "state": {"counter": 10},
        "messages": [],
        "metadata": {},
        "parent_checkpoint_id": None,
    }

    checkpoint = Checkpoint.from_dict(data)

    assert checkpoint.checkpoint_id == "checkpoint-1"
    assert isinstance(checkpoint.timestamp, datetime)


def test_checkpoint_json_serialization():
    """Test JSON serialization round-trip."""
    original = Checkpoint(
        checkpoint_id="checkpoint-1",
        session_id="session-1",
        agent_name="assistant",
        timestamp=datetime.now(timezone.utc),
        step_number=10,
        state={"counter": 10, "data": [1, 2, 3]},
        messages=[],
        metadata={"cost": 0.05},
    )

    # Serialize
    json_str = original.to_json()

    # Deserialize
    restored = Checkpoint.from_json(json_str)

    assert restored.checkpoint_id == original.checkpoint_id
    assert restored.state == original.state
    assert restored.metadata == original.metadata


# ===== InMemoryCheckpointStorage Tests =====


@pytest.mark.asyncio
async def test_inmemory_save_and_load():
    """Test saving and loading checkpoints in memory."""
    storage = InMemoryCheckpointStorage()

    checkpoint = Checkpoint(
        checkpoint_id="checkpoint-1",
        session_id="session-1",
        agent_name="assistant",
        timestamp=datetime.now(timezone.utc),
        step_number=10,
        state={"counter": 10},
        messages=[],
        metadata={},
    )

    await storage.save(checkpoint)
    loaded = await storage.load("checkpoint-1")

    assert loaded is not None
    assert loaded.checkpoint_id == "checkpoint-1"
    assert loaded.state["counter"] == 10


@pytest.mark.asyncio
async def test_inmemory_list_checkpoints():
    """Test listing checkpoints for a session."""
    storage = InMemoryCheckpointStorage()

    # Create multiple checkpoints
    for i in range(5):
        checkpoint = Checkpoint(
            checkpoint_id=f"checkpoint-{i}",
            session_id="session-1",
            agent_name="assistant",
            timestamp=datetime.now(timezone.utc),
            step_number=i,
            state={"counter": i},
            messages=[],
            metadata={},
        )
        await storage.save(checkpoint)

    checkpoints = await storage.list_checkpoints("session-1")

    assert len(checkpoints) == 5
    # Should be ordered by timestamp (most recent first)
    assert checkpoints[0].step_number >= checkpoints[-1].step_number


@pytest.mark.asyncio
async def test_inmemory_get_latest():
    """Test getting latest checkpoint."""
    storage = InMemoryCheckpointStorage()

    # Create checkpoints
    for i in range(3):
        checkpoint = Checkpoint(
            checkpoint_id=f"checkpoint-{i}",
            session_id="session-1",
            agent_name="assistant",
            timestamp=datetime.now(timezone.utc),
            step_number=i,
            state={"counter": i},
            messages=[],
            metadata={},
        )
        await storage.save(checkpoint)

    latest = await storage.get_latest("session-1")

    assert latest is not None
    assert latest.step_number == 2  # Last one


@pytest.mark.asyncio
async def test_inmemory_delete():
    """Test deleting a checkpoint."""
    storage = InMemoryCheckpointStorage()

    checkpoint = Checkpoint(
        checkpoint_id="checkpoint-1",
        session_id="session-1",
        agent_name="assistant",
        timestamp=datetime.now(timezone.utc),
        step_number=10,
        state={},
        messages=[],
        metadata={},
    )

    await storage.save(checkpoint)
    deleted = await storage.delete("checkpoint-1")

    assert deleted is True

    loaded = await storage.load("checkpoint-1")
    assert loaded is None


@pytest.mark.asyncio
async def test_inmemory_delete_session():
    """Test deleting all checkpoints for a session."""
    storage = InMemoryCheckpointStorage()

    # Create checkpoints for multiple sessions
    for session_num in range(1, 3):
        for i in range(3):
            checkpoint = Checkpoint(
                checkpoint_id=f"s{session_num}-checkpoint-{i}",
                session_id=f"session-{session_num}",
                agent_name="assistant",
                timestamp=datetime.now(timezone.utc),
                step_number=i,
                state={},
                messages=[],
                metadata={},
            )
            await storage.save(checkpoint)

    # Delete session 1
    count = await storage.delete_session("session-1")
    assert count == 3

    # Session 1 should be empty
    session1_checkpoints = await storage.list_checkpoints("session-1")
    assert len(session1_checkpoints) == 0

    # Session 2 should still exist
    session2_checkpoints = await storage.list_checkpoints("session-2")
    assert len(session2_checkpoints) == 3


@pytest.mark.asyncio
async def test_inmemory_checkpoint_history():
    """Test getting checkpoint history by following parent links."""
    storage = InMemoryCheckpointStorage()

    # Create chain of checkpoints
    parent_id = None
    for i in range(5):
        checkpoint = Checkpoint(
            checkpoint_id=f"checkpoint-{i}",
            session_id="session-1",
            agent_name="assistant",
            timestamp=datetime.now(timezone.utc),
            step_number=i,
            state={"counter": i},
            messages=[],
            metadata={},
            parent_checkpoint_id=parent_id,
        )
        await storage.save(checkpoint)
        parent_id = f"checkpoint-{i}"

    # Get history from last checkpoint
    history = await storage.get_checkpoint_history("checkpoint-4", max_depth=10)

    assert len(history) == 5
    assert history[0].checkpoint_id == "checkpoint-4"
    assert history[-1].checkpoint_id == "checkpoint-0"


# ===== FileCheckpointStorage Tests =====


@pytest.fixture
def temp_checkpoint_dir():
    """Create temporary directory for file storage tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_file_save_and_load(temp_checkpoint_dir):
    """Test saving and loading checkpoints to files."""
    storage = FileCheckpointStorage(temp_checkpoint_dir)

    checkpoint = Checkpoint(
        checkpoint_id="checkpoint-1",
        session_id="session-1",
        agent_name="assistant",
        timestamp=datetime.now(timezone.utc),
        step_number=10,
        state={"counter": 10},
        messages=[],
        metadata={},
    )

    await storage.save(checkpoint)
    loaded = await storage.load("checkpoint-1")

    assert loaded is not None
    assert loaded.checkpoint_id == "checkpoint-1"
    assert loaded.state["counter"] == 10


@pytest.mark.asyncio
async def test_file_persistence(temp_checkpoint_dir):
    """Test that checkpoints persist across storage instances."""
    # Create storage and save checkpoint
    storage1 = FileCheckpointStorage(temp_checkpoint_dir)

    checkpoint = Checkpoint(
        checkpoint_id="checkpoint-1",
        session_id="session-1",
        agent_name="assistant",
        timestamp=datetime.now(timezone.utc),
        step_number=10,
        state={"counter": 10},
        messages=[],
        metadata={},
    )

    await storage1.save(checkpoint)

    # Create new storage instance (simulates restart)
    storage2 = FileCheckpointStorage(temp_checkpoint_dir)

    loaded = await storage2.load("checkpoint-1")

    assert loaded is not None
    assert loaded.checkpoint_id == "checkpoint-1"


@pytest.mark.asyncio
async def test_file_get_stats(temp_checkpoint_dir):
    """Test getting storage statistics."""
    storage = FileCheckpointStorage(temp_checkpoint_dir)

    # Create some checkpoints
    for i in range(3):
        checkpoint = Checkpoint(
            checkpoint_id=f"checkpoint-{i}",
            session_id="session-1",
            agent_name="assistant",
            timestamp=datetime.now(timezone.utc),
            step_number=i,
            state={},
            messages=[],
            metadata={},
        )
        await storage.save(checkpoint)

    stats = storage.get_stats()

    assert stats["total_checkpoints"] == 3
    assert stats["total_sessions"] == 1
    assert stats["disk_usage_bytes"] > 0


# ===== CheckpointManager Tests =====


@pytest.mark.asyncio
async def test_manager_create_checkpoint():
    """Test creating checkpoints with manager."""
    manager = CheckpointManager()

    checkpoint_id = await manager.create_checkpoint(
        session_id="session-1",
        agent_name="assistant",
        step_number=10,
        state={"counter": 10},
        messages=[Message(role="user", content="Hello")],
        metadata={"cost": 0.05},
    )

    assert checkpoint_id is not None

    # Load and verify
    checkpoint = await manager.load_checkpoint(checkpoint_id)
    assert checkpoint.step_number == 10
    assert checkpoint.state["counter"] == 10


@pytest.mark.asyncio
async def test_manager_auto_checkpoint():
    """Test automatic checkpointing based on interval."""
    manager = CheckpointManager(auto_checkpoint_interval=5)

    # Steps 1-4: Should not checkpoint
    for step in range(1, 5):
        should = await manager.should_checkpoint("session-1", step)
        assert should is False

    # Step 5: Should checkpoint
    should = await manager.should_checkpoint("session-1", 5)
    assert should is True


@pytest.mark.asyncio
async def test_manager_restore_state():
    """Test restoring state from checkpoint."""
    manager = CheckpointManager()

    # Create checkpoint
    checkpoint_id = await manager.create_checkpoint(
        session_id="session-1",
        agent_name="assistant",
        step_number=10,
        state={"counter": 10, "mode": "active"},
        messages=[],
        metadata={},
    )

    # Load and restore
    checkpoint = await manager.load_checkpoint(checkpoint_id)
    state = await manager.restore_state(checkpoint)

    assert state["counter"] == 10
    assert state["mode"] == "active"


@pytest.mark.asyncio
async def test_manager_prune_old_checkpoints():
    """Test pruning old checkpoints."""
    manager = CheckpointManager()

    # Create 10 checkpoints
    for i in range(10):
        await manager.create_checkpoint(
            session_id="session-1",
            agent_name="assistant",
            step_number=i,
            state={"counter": i},
            messages=[],
            metadata={},
        )

    # Keep only last 5
    deleted = await manager.prune_old_checkpoints("session-1", keep_last=5)

    assert deleted == 5

    # Verify only 5 remain
    checkpoints = await manager.list_checkpoints("session-1")
    assert len(checkpoints) == 5


@pytest.mark.asyncio
async def test_manager_session_stats():
    """Test getting session statistics."""
    manager = CheckpointManager()

    # Create checkpoints
    for i in range(5):
        await manager.create_checkpoint(
            session_id="session-1",
            agent_name="assistant",
            step_number=i * 10,
            state={},
            messages=[],
            metadata={},
        )

    stats = await manager.get_session_stats("session-1")

    assert stats["total_checkpoints"] == 5
    assert stats["first_step"] == 0
    assert stats["latest_step"] == 40
    assert stats["steps_covered"] == 40
