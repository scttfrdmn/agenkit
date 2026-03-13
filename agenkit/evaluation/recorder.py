"""
Session recording and replay for evaluation.

Records agent interactions for later replay, analysis, and A/B testing.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from ..interfaces import Agent, Message


@dataclass
class InteractionRecord:
    """
    Record of single agent interaction.

    Contains input, output, timing, and metadata.
    """

    interaction_id: str
    session_id: str
    input_message: dict[str, Any]
    output_message: dict[str, Any]
    timestamp: datetime
    latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "interaction_id": self.interaction_id,
            "session_id": self.session_id,
            "input_message": self.input_message,
            "output_message": self.output_message,
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InteractionRecord":
        """Create from dictionary."""
        return cls(
            interaction_id=data["interaction_id"],
            session_id=data["session_id"],
            input_message=data["input_message"],
            output_message=data["output_message"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            latency_ms=data["latency_ms"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionRecording:
    """
    Recording of entire session.

    Contains all interactions and session metadata.
    """

    session_id: str
    agent_name: str
    start_time: datetime
    end_time: datetime | None = None
    interactions: list[InteractionRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Calculate session duration in seconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    @property
    def interaction_count(self) -> int:
        """Get number of interactions."""
        return len(self.interactions)

    @property
    def total_latency_ms(self) -> float:
        """Get total latency across all interactions."""
        return sum(i.latency_ms for i in self.interactions)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "interactions": [i.to_dict() for i in self.interactions],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionRecording":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            agent_name=data["agent_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            interactions=[InteractionRecord.from_dict(i) for i in data.get("interactions", [])],
            metadata=data.get("metadata", {}),
        )


class RecordingStorage(Protocol):
    """
    Protocol for recording storage backends.

    Implement this to create custom storage (Redis, S3, Postgres, etc.).
    """

    async def save_recording(self, recording: SessionRecording) -> None:
        """Save recording."""
        ...

    async def load_recording(self, session_id: str) -> SessionRecording | None:
        """Load recording by session ID."""
        ...

    async def list_recordings(self, limit: int = 100, offset: int = 0) -> list[SessionRecording]:
        """List recordings."""
        ...

    async def delete_recording(self, session_id: str) -> None:
        """Delete recording."""
        ...


class LocalRecordingStorage:
    """
    File-based recording storage.

    Stores recordings as JSON files on disk.
    """

    def __init__(self, recordings_dir: str = "./recordings"):
        """
        Initialize file storage.

        Args:
            recordings_dir: Directory to store recordings
        """
        self.recordings_dir = Path(recordings_dir)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

    async def save_recording(self, recording: SessionRecording) -> None:
        """Save recording to file."""
        file_path = self.recordings_dir / f"{recording.session_id}.json"
        with open(file_path, "w") as f:
            json.dump(recording.to_dict(), f, indent=2)

    async def load_recording(self, session_id: str) -> SessionRecording | None:
        """Load recording from file."""
        file_path = self.recordings_dir / f"{session_id}.json"
        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)
            return SessionRecording.from_dict(data)

    async def list_recordings(self, limit: int = 100, offset: int = 0) -> list[SessionRecording]:
        """List all recordings."""
        recordings = []
        json_files = sorted(
            self.recordings_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        for file_path in json_files[offset : offset + limit]:
            with open(file_path) as f:
                data = json.load(f)
                recordings.append(SessionRecording.from_dict(data))

        return recordings

    async def delete_recording(self, session_id: str) -> None:
        """Delete recording file."""
        file_path = self.recordings_dir / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()


class MemoryRecordingStorage:
    """
    In-memory recording storage for testing.

    Does not persist recordings across restarts.
    """

    def __init__(self):
        self._recordings: dict[str, SessionRecording] = {}

    async def save_recording(self, recording: SessionRecording) -> None:
        """Save recording to memory."""
        self._recordings[recording.session_id] = recording

    async def load_recording(self, session_id: str) -> SessionRecording | None:
        """Load recording from memory."""
        return self._recordings.get(session_id)

    async def list_recordings(self, limit: int = 100, offset: int = 0) -> list[SessionRecording]:
        """List recordings from memory."""
        recordings = list(self._recordings.values())
        # Sort by start time (most recent first)
        recordings.sort(key=lambda r: r.start_time, reverse=True)
        return recordings[offset : offset + limit]

    async def delete_recording(self, session_id: str) -> None:
        """Delete recording from memory."""
        self._recordings.pop(session_id, None)


class SessionRecorder:
    """
    Record agent sessions for replay and analysis.

    Automatically records all interactions with an agent,
    storing inputs, outputs, timing, and metadata.

    Example:
        >>> recorder = SessionRecorder(storage=FileRecordingStorage())
        >>> wrapped_agent = recorder.wrap(agent)
        >>>
        >>> # Use agent normally (automatically recorded)
        >>> response = await wrapped_agent.process(message, session_id="test-123")
        >>>
        >>> # Save recording
        >>> await recorder.finalize_session("test-123")
        >>>
        >>> # Later: replay session
        >>> recording = await recorder.load_recording("test-123")
    """

    def __init__(self, storage: RecordingStorage | None = None):
        """
        Initialize session recorder.

        Args:
            storage: Storage backend (defaults to in-memory)
        """
        self.storage = storage or MemoryRecordingStorage()
        self._active_sessions: dict[str, SessionRecording] = {}

    def wrap(self, agent: Agent) -> Agent:
        """
        Wrap agent to record interactions.

        Args:
            agent: Agent to wrap

        Returns:
            Wrapped agent that records all interactions
        """

        # Create inline wrapper
        class RecordingWrapper:
            def __init__(self, base_agent: Agent, recorder: "SessionRecorder"):
                self._agent = base_agent
                self._recorder = recorder
                self.name = getattr(base_agent, "name", "recording_wrapper")

            async def process(self, message: Message, session_id: str | None = None) -> Message:
                import time

                sid = session_id or "default"

                # Start session if not already started
                if sid not in self._recorder._active_sessions:
                    await self._recorder.start_session(sid, self.name)

                # Process with timing
                start = time.perf_counter()
                output = await self._agent.process(message, session_id=session_id)
                latency = (time.perf_counter() - start) * 1000

                # Record interaction
                await self._recorder.record_interaction(sid, message, output, latency)

                return output

        return RecordingWrapper(agent, self)  # type: ignore

    async def start_session(
        self, session_id: str, agent_name: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Start recording session.

        Args:
            session_id: Session identifier
            agent_name: Name of agent being recorded
            metadata: Optional session metadata
        """
        self._active_sessions[session_id] = SessionRecording(
            session_id=session_id,
            agent_name=agent_name,
            start_time=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

    async def record_interaction(
        self,
        session_id: str,
        input_message: Message,
        output_message: Message,
        latency_ms: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Record single interaction.

        Args:
            session_id: Session identifier
            input_message: Input to agent
            output_message: Agent response
            latency_ms: Processing time in milliseconds
            metadata: Optional interaction metadata
        """
        import uuid

        # Get or create session
        if session_id not in self._active_sessions:
            await self.start_session(session_id, "unknown")

        session = self._active_sessions[session_id]

        # Create interaction record
        record = InteractionRecord(
            interaction_id=str(uuid.uuid4()),
            session_id=session_id,
            input_message=self._message_to_dict(input_message),
            output_message=self._message_to_dict(output_message),
            timestamp=datetime.now(timezone.utc),
            latency_ms=latency_ms,
            metadata=metadata or {},
        )

        session.interactions.append(record)

    async def finalize_session(self, session_id: str) -> SessionRecording:
        """
        Finalize and save session recording.

        Args:
            session_id: Session to finalize

        Returns:
            Session recording
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"No active session: {session_id}")

        session = self._active_sessions.pop(session_id)
        session.end_time = datetime.now(timezone.utc)

        # Save to storage
        await self.storage.save_recording(session)

        return session

    async def load_recording(self, session_id: str) -> SessionRecording | None:
        """
        Load recording from storage.

        Args:
            session_id: Session to load

        Returns:
            Session recording if found
        """
        return await self.storage.load_recording(session_id)

    async def list_recordings(self, limit: int = 100, offset: int = 0) -> list[SessionRecording]:
        """List all recordings."""
        return await self.storage.list_recordings(limit, offset)

    async def delete_recording(self, session_id: str) -> None:
        """Delete recording."""
        await self.storage.delete_recording(session_id)

    def _message_to_dict(self, message: Message) -> dict:
        """Convert message to dictionary."""
        return {
            "role": message.role,
            "content": message.content,
            "metadata": message.metadata or {},
        }


# Deprecated aliases — use new names in new code.
FileRecordingStorage = LocalRecordingStorage  # Deprecated: Use LocalRecordingStorage instead.
InMemoryRecordingStorage = MemoryRecordingStorage  # Deprecated: Use MemoryRecordingStorage instead.

class SessionReplay:
    """
    Replay recorded sessions for analysis and A/B testing.

    Takes recorded session and replays it through a (possibly different)
    agent to compare behavior.

    Example:
        >>> replay = SessionReplay()
        >>> recording = await recorder.load_recording("test-123")
        >>>
        >>> # Replay with original agent
        >>> results_a = await replay.replay(recording, agent_v1)
        >>>
        >>> # Replay with new agent (A/B test)
        >>> results_b = await replay.replay(recording, agent_v2)
        >>>
        >>> # Compare
        >>> comparison = replay.compare(results_a, results_b)
    """

    async def replay(
        self, recording: SessionRecording, agent: Agent, session_id: str | None = None
    ) -> dict[str, Any]:
        """
        Replay session through agent.

        Args:
            recording: Session recording to replay
            agent: Agent to replay through
            session_id: Optional session ID (defaults to original)

        Returns:
            Replay results with outputs and metrics
        """
        import time

        session_id = session_id or recording.session_id
        results = {
            "session_id": session_id,
            "original_session_id": recording.session_id,
            "interactions": [],
            "total_latency_ms": 0.0,
            "error_count": 0,
        }

        for interaction in recording.interactions:
            # Reconstruct input message
            input_msg = Message(
                role=interaction.input_message["role"],
                content=interaction.input_message["content"],
                metadata=interaction.input_message.get("metadata", {}),
            )

            try:
                # Replay through agent
                start = time.perf_counter()
                output_msg = await agent.process(input_msg, session_id=session_id)
                latency = (time.perf_counter() - start) * 1000

                results["interactions"].append(
                    {
                        "input": interaction.input_message,
                        "original_output": interaction.output_message,
                        "replay_output": self._message_to_dict(output_msg),
                        "original_latency_ms": interaction.latency_ms,
                        "replay_latency_ms": latency,
                    }
                )

                results["total_latency_ms"] += latency

            except Exception as e:
                results["error_count"] += 1
                results["interactions"].append(
                    {
                        "input": interaction.input_message,
                        "original_output": interaction.output_message,
                        "error": str(e),
                    }
                )

        return results

    async def compare(self, results_a: dict[str, Any], results_b: dict[str, Any]) -> dict[str, Any]:
        """
        Compare two replay results.

        Useful for A/B testing different agent versions.

        Args:
            results_a: First replay results
            results_b: Second replay results

        Returns:
            Comparison metrics
        """
        comparison = {
            "interaction_count": len(results_a["interactions"]),
            "latency_diff_ms": results_b["total_latency_ms"] - results_a["total_latency_ms"],
            "latency_diff_percent": (
                (
                    (results_b["total_latency_ms"] - results_a["total_latency_ms"])
                    / results_a["total_latency_ms"]
                    * 100
                )
                if results_a["total_latency_ms"] > 0
                else 0
            ),
            "error_diff": results_b["error_count"] - results_a["error_count"],
            "output_differences": [],
        }

        # Compare outputs
        for i, (ia, ib) in enumerate(
            zip(results_a["interactions"], results_b["interactions"], strict=False)
        ):
            if "error" in ia or "error" in ib:
                continue

            output_a = ia.get("replay_output", {}).get("content", "")
            output_b = ib.get("replay_output", {}).get("content", "")

            if output_a != output_b:
                comparison["output_differences"].append(
                    {"interaction_index": i, "output_a": output_a, "output_b": output_b}
                )

        return comparison

    def _message_to_dict(self, message: Message) -> dict:
        """Convert message to dictionary."""
        return {
            "role": message.role,
            "content": message.content,
            "metadata": message.metadata or {},
        }
