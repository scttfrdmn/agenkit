"""
Tests for session recording and replay.

Tests SessionRecorder, SessionReplay, and storage backends.
"""

import pytest
from agenkit.evaluation.recorder import (
    SessionRecorder,
    SessionReplay,
    InMemoryRecordingStorage,
    FileRecordingStorage,
    InteractionRecord,
    SessionRecording
)
from agenkit.interfaces import Message
from datetime import datetime, timezone
import tempfile
import shutil


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, responses=None):
        self.responses = responses or ["Response"]
        self.call_count = 0
        self.name = "mock_agent"

    async def process(self, message: Message, session_id=None):
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return Message(role="assistant", content=response)


@pytest.mark.asyncio
async def test_session_recorder_basic():
    """Test basic session recording."""
    storage = InMemoryRecordingStorage()
    recorder = SessionRecorder(storage=storage)

    await recorder.start_session("test-session", "test_agent")

    input_msg = Message(role="user", content="Hello")
    output_msg = Message(role="assistant", content="Hi there")

    await recorder.record_interaction(
        "test-session",
        input_msg,
        output_msg,
        latency_ms=10.5
    )

    recording = await recorder.finalize_session("test-session")

    assert recording.session_id == "test-session"
    assert recording.agent_name == "test_agent"
    assert recording.interaction_count == 1
    assert recording.interactions[0].latency_ms == 10.5


@pytest.mark.asyncio
async def test_session_recorder_multiple_interactions():
    """Test recording multiple interactions."""
    storage = InMemoryRecordingStorage()
    recorder = SessionRecorder(storage=storage)

    await recorder.start_session("test-session", "test_agent")

    for i in range(5):
        input_msg = Message(role="user", content=f"Message {i}")
        output_msg = Message(role="assistant", content=f"Response {i}")

        await recorder.record_interaction(
            "test-session",
            input_msg,
            output_msg,
            latency_ms=10.0 + i
        )

    recording = await recorder.finalize_session("test-session")

    assert recording.interaction_count == 5
    assert recording.total_latency_ms == sum(10.0 + i for i in range(5))


@pytest.mark.asyncio
async def test_session_recorder_auto_start():
    """Test auto-start of session if not explicitly started."""
    storage = InMemoryRecordingStorage()
    recorder = SessionRecorder(storage=storage)

    # Record without starting session (should auto-start)
    input_msg = Message(role="user", content="Hello")
    output_msg = Message(role="assistant", content="Response")

    await recorder.record_interaction(
        "auto-session",
        input_msg,
        output_msg,
        latency_ms=10.0
    )

    recording = await recorder.finalize_session("auto-session")

    assert recording.interaction_count == 1


@pytest.mark.asyncio
async def test_session_recorder_wrap_agent():
    """Test wrapping agent for automatic recording."""
    storage = InMemoryRecordingStorage()
    recorder = SessionRecorder(storage=storage)

    agent = MockAgent(responses=["Response 1", "Response 2"])
    wrapped = recorder.wrap(agent)

    # Use wrapped agent
    msg1 = Message(role="user", content="Hello")
    await wrapped.process(msg1, session_id="test-session")

    msg2 = Message(role="user", content="How are you?")
    await wrapped.process(msg2, session_id="test-session")

    # Finalize and check recording
    recording = await recorder.finalize_session("test-session")

    assert recording.interaction_count == 2
    assert recording.interactions[0].input_message["content"] == "Hello"
    assert recording.interactions[1].input_message["content"] == "How are you?"


@pytest.mark.asyncio
async def test_session_recorder_load():
    """Test loading recording from storage."""
    storage = InMemoryRecordingStorage()
    recorder = SessionRecorder(storage=storage)

    await recorder.start_session("test-session", "test_agent")

    input_msg = Message(role="user", content="Hello")
    output_msg = Message(role="assistant", content="Response")

    await recorder.record_interaction(
        "test-session",
        input_msg,
        output_msg,
        latency_ms=10.0
    )

    await recorder.finalize_session("test-session")

    # Load recording
    loaded = await recorder.load_recording("test-session")

    assert loaded is not None
    assert loaded.session_id == "test-session"
    assert loaded.interaction_count == 1


@pytest.mark.asyncio
async def test_session_recorder_list():
    """Test listing recordings."""
    storage = InMemoryRecordingStorage()
    recorder = SessionRecorder(storage=storage)

    # Create multiple recordings
    for i in range(3):
        await recorder.start_session(f"session-{i}", "test_agent")
        await recorder.record_interaction(
            f"session-{i}",
            Message(role="user", content="Test"),
            Message(role="assistant", content="Response"),
            latency_ms=10.0
        )
        await recorder.finalize_session(f"session-{i}")

    recordings = await recorder.list_recordings()

    assert len(recordings) == 3


@pytest.mark.asyncio
async def test_session_recorder_delete():
    """Test deleting recording."""
    storage = InMemoryRecordingStorage()
    recorder = SessionRecorder(storage=storage)

    await recorder.start_session("test-session", "test_agent")
    await recorder.record_interaction(
        "test-session",
        Message(role="user", content="Test"),
        Message(role="assistant", content="Response"),
        latency_ms=10.0
    )
    await recorder.finalize_session("test-session")

    # Delete
    await recorder.delete_recording("test-session")

    # Verify deleted
    loaded = await recorder.load_recording("test-session")
    assert loaded is None


@pytest.mark.asyncio
async def test_file_recording_storage():
    """Test file-based recording storage."""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        storage = FileRecordingStorage(recordings_dir=temp_dir)
        recorder = SessionRecorder(storage=storage)

        await recorder.start_session("test-session", "test_agent")
        await recorder.record_interaction(
            "test-session",
            Message(role="user", content="Test"),
            Message(role="assistant", content="Response"),
            latency_ms=10.0
        )
        await recorder.finalize_session("test-session")

        # Load from file
        loaded = await recorder.load_recording("test-session")

        assert loaded is not None
        assert loaded.session_id == "test-session"

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_session_replay_basic():
    """Test replaying recorded session."""
    # Record session
    storage = InMemoryRecordingStorage()
    recorder = SessionRecorder(storage=storage)

    agent = MockAgent(responses=["Original response"])
    wrapped = recorder.wrap(agent)

    await wrapped.process(Message(role="user", content="Hello"), session_id="test")

    recording = await recorder.finalize_session("test")

    # Replay with different agent
    replay_agent = MockAgent(responses=["Replayed response"])
    replay = SessionReplay()

    results = await replay.replay(recording, replay_agent, session_id="replay")

    assert results["session_id"] == "replay"
    assert results["original_session_id"] == "test"
    assert len(results["interactions"]) == 1
    assert results["error_count"] == 0


@pytest.mark.asyncio
async def test_session_replay_multiple_interactions():
    """Test replaying session with multiple interactions."""
    # Record session
    storage = InMemoryRecordingStorage()
    recorder = SessionRecorder(storage=storage)

    agent = MockAgent(responses=["Response 1", "Response 2", "Response 3"])
    wrapped = recorder.wrap(agent)

    for i in range(3):
        await wrapped.process(
            Message(role="user", content=f"Message {i}"),
            session_id="test"
        )

    recording = await recorder.finalize_session("test")

    # Replay
    replay_agent = MockAgent(responses=["Replay A", "Replay B", "Replay C"])
    replay = SessionReplay()

    results = await replay.replay(recording, replay_agent)

    assert len(results["interactions"]) == 3
    assert results["error_count"] == 0


@pytest.mark.asyncio
async def test_session_replay_with_errors():
    """Test replay handling agent errors."""

    class FailingAgent:
        async def process(self, message, session_id=None):
            raise ValueError("Agent error")

    # Create simple recording
    recording = SessionRecording(
        session_id="test",
        agent_name="test_agent",
        start_time=datetime.now(timezone.utc),
        interactions=[
            InteractionRecord(
                interaction_id="1",
                session_id="test",
                input_message={"role": "user", "content": "Hello", "metadata": {}},
                output_message={"role": "assistant", "content": "Response", "metadata": {}},
                timestamp=datetime.now(timezone.utc),
                latency_ms=10.0
            )
        ]
    )

    replay = SessionReplay()
    results = await replay.replay(recording, FailingAgent())

    assert results["error_count"] == 1
    assert "error" in results["interactions"][0]


@pytest.mark.asyncio
async def test_session_replay_compare():
    """Test comparing two replay results."""
    # Create simple recording
    recording = SessionRecording(
        session_id="test",
        agent_name="test_agent",
        start_time=datetime.now(timezone.utc),
        interactions=[
            InteractionRecord(
                interaction_id="1",
                session_id="test",
                input_message={"role": "user", "content": "Hello", "metadata": {}},
                output_message={"role": "assistant", "content": "Original", "metadata": {}},
                timestamp=datetime.now(timezone.utc),
                latency_ms=10.0
            )
        ]
    )

    # Replay with two different agents
    agent_a = MockAgent(responses=["Response A"])
    agent_b = MockAgent(responses=["Response B"])

    replay = SessionReplay()
    results_a = await replay.replay(recording, agent_a)
    results_b = await replay.replay(recording, agent_b)

    # Compare
    comparison = await replay.compare(results_a, results_b)

    assert comparison["interaction_count"] == 1
    assert "latency_diff_ms" in comparison
    assert "output_differences" in comparison


def test_interaction_record_serialization():
    """Test InteractionRecord to/from dict."""
    record = InteractionRecord(
        interaction_id="test-123",
        session_id="session-1",
        input_message={"role": "user", "content": "Hello"},
        output_message={"role": "assistant", "content": "Hi"},
        timestamp=datetime.now(timezone.utc),
        latency_ms=10.5
    )

    data = record.to_dict()

    assert data["interaction_id"] == "test-123"
    assert data["latency_ms"] == 10.5

    # Deserialize
    loaded = InteractionRecord.from_dict(data)

    assert loaded.interaction_id == record.interaction_id
    assert loaded.latency_ms == record.latency_ms


def test_session_recording_properties():
    """Test SessionRecording computed properties."""
    recording = SessionRecording(
        session_id="test",
        agent_name="test_agent",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        interactions=[
            InteractionRecord(
                interaction_id="1",
                session_id="test",
                input_message={},
                output_message={},
                timestamp=datetime.now(timezone.utc),
                latency_ms=10.0
            ),
            InteractionRecord(
                interaction_id="2",
                session_id="test",
                input_message={},
                output_message={},
                timestamp=datetime.now(timezone.utc),
                latency_ms=20.0
            )
        ]
    )

    assert recording.interaction_count == 2
    assert recording.total_latency_ms == 30.0
    assert recording.duration_seconds >= 0
