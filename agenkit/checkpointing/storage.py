"""
Checkpoint storage implementations.

Provides in-memory and file-based storage for checkpoints.
"""

from collections import defaultdict
from pathlib import Path

from .checkpoint import Checkpoint, CheckpointStorage


class InMemoryCheckpointStorage(CheckpointStorage):
    """
    In-memory checkpoint storage.

    Good for:
    - Testing
    - Development
    - Short-lived sessions

    Not suitable for:
    - Production (no persistence)
    - Long-running agents (lost on restart)
    """

    def __init__(self):
        # checkpoint_id -> Checkpoint
        self._checkpoints: dict[str, Checkpoint] = {}
        # session_id -> list of checkpoint_ids (ordered by timestamp)
        self._session_checkpoints: dict[str, list[str]] = defaultdict(list)

    async def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to memory."""
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint

        # Add to session index
        if checkpoint.checkpoint_id not in self._session_checkpoints[checkpoint.session_id]:
            self._session_checkpoints[checkpoint.session_id].append(checkpoint.checkpoint_id)

            # Sort by timestamp (most recent first)
            self._session_checkpoints[checkpoint.session_id].sort(
                key=lambda cid: self._checkpoints[cid].timestamp, reverse=True
            )

    async def load(self, checkpoint_id: str) -> Checkpoint | None:
        """Load checkpoint from memory."""
        return self._checkpoints.get(checkpoint_id)

    async def list_checkpoints(self, session_id: str, limit: int | None = None) -> list[Checkpoint]:
        """List checkpoints for session."""
        checkpoint_ids = self._session_checkpoints.get(session_id, [])

        if limit:
            checkpoint_ids = checkpoint_ids[:limit]

        return [self._checkpoints[cid] for cid in checkpoint_ids]

    async def get_latest(self, session_id: str) -> Checkpoint | None:
        """Get latest checkpoint for session."""
        checkpoints = await self.list_checkpoints(session_id, limit=1)
        return checkpoints[0] if checkpoints else None

    async def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint."""
        if checkpoint_id not in self._checkpoints:
            return False

        checkpoint = self._checkpoints[checkpoint_id]
        del self._checkpoints[checkpoint_id]

        # Remove from session index
        if checkpoint_id in self._session_checkpoints[checkpoint.session_id]:
            self._session_checkpoints[checkpoint.session_id].remove(checkpoint_id)

        return True

    async def delete_session(self, session_id: str) -> int:
        """Delete all checkpoints for session."""
        checkpoint_ids = self._session_checkpoints.get(session_id, [])
        count = len(checkpoint_ids)

        for checkpoint_id in checkpoint_ids:
            del self._checkpoints[checkpoint_id]

        del self._session_checkpoints[session_id]

        return count

    async def get_checkpoint_history(
        self, checkpoint_id: str, max_depth: int = 10
    ) -> list[Checkpoint]:
        """Get checkpoint history by following parent links."""
        history = []
        current_id = checkpoint_id

        for _ in range(max_depth):
            checkpoint = await self.load(current_id)
            if not checkpoint:
                break

            history.append(checkpoint)

            if not checkpoint.parent_checkpoint_id:
                break

            current_id = checkpoint.parent_checkpoint_id

        return history

    def get_stats(self) -> dict:
        """Get storage statistics."""
        return {
            "total_checkpoints": len(self._checkpoints),
            "total_sessions": len(self._session_checkpoints),
            "checkpoints_per_session": {
                session_id: len(checkpoint_ids)
                for session_id, checkpoint_ids in self._session_checkpoints.items()
            },
        }


class FileCheckpointStorage(CheckpointStorage):
    """
    File-based checkpoint storage.

    Stores each checkpoint as a JSON file on disk for persistence.

    Directory structure:
        checkpoint_dir/
            {session_id}/
                {checkpoint_id}.json
                {checkpoint_id}.json
                ...

    Good for:
    - Production (persistent)
    - Single-machine deployments
    - Development with persistence

    Example:
        >>> storage = FileCheckpointStorage("./checkpoints")
        >>> await storage.save(checkpoint)
    """

    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        """
        Initialize file-based storage.

        Args:
            checkpoint_dir: Directory to store checkpoints
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_dir(self, session_id: str) -> Path:
        """Get directory for session checkpoints."""
        session_dir = self.checkpoint_dir / session_id
        session_dir.mkdir(exist_ok=True)
        return session_dir

    def _get_checkpoint_path(self, session_id: str, checkpoint_id: str) -> Path:
        """Get file path for checkpoint."""
        return self._get_session_dir(session_id) / f"{checkpoint_id}.json"

    async def save(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to file."""
        checkpoint_path = self._get_checkpoint_path(checkpoint.session_id, checkpoint.checkpoint_id)

        with open(checkpoint_path, "w") as f:
            f.write(checkpoint.to_json())

    async def load(self, checkpoint_id: str) -> Checkpoint | None:
        """Load checkpoint from file."""
        # Need to search through session directories
        for session_dir in self.checkpoint_dir.iterdir():
            if not session_dir.is_dir():
                continue

            checkpoint_path = session_dir / f"{checkpoint_id}.json"
            if checkpoint_path.exists():
                with open(checkpoint_path) as f:
                    return Checkpoint.from_json(f.read())

        return None

    async def list_checkpoints(self, session_id: str, limit: int | None = None) -> list[Checkpoint]:
        """List checkpoints for session."""
        session_dir = self._get_session_dir(session_id)

        if not session_dir.exists():
            return []

        # Load all checkpoints
        checkpoints = []
        for checkpoint_file in session_dir.glob("*.json"):
            with open(checkpoint_file) as f:
                checkpoint = Checkpoint.from_json(f.read())
                checkpoints.append(checkpoint)

        # Sort by timestamp (most recent first)
        checkpoints.sort(key=lambda c: c.timestamp, reverse=True)

        if limit:
            checkpoints = checkpoints[:limit]

        return checkpoints

    async def get_latest(self, session_id: str) -> Checkpoint | None:
        """Get latest checkpoint for session."""
        checkpoints = await self.list_checkpoints(session_id, limit=1)
        return checkpoints[0] if checkpoints else None

    async def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint file."""
        # Search through session directories
        for session_dir in self.checkpoint_dir.iterdir():
            if not session_dir.is_dir():
                continue

            checkpoint_path = session_dir / f"{checkpoint_id}.json"
            if checkpoint_path.exists():
                checkpoint_path.unlink()
                return True

        return False

    async def delete_session(self, session_id: str) -> int:
        """Delete all checkpoints for session."""
        session_dir = self._get_session_dir(session_id)

        if not session_dir.exists():
            return 0

        # Count and delete checkpoint files
        checkpoint_files = list(session_dir.glob("*.json"))
        count = len(checkpoint_files)

        for checkpoint_file in checkpoint_files:
            checkpoint_file.unlink()

        # Remove session directory if empty
        try:
            session_dir.rmdir()
        except OSError:
            pass  # Directory not empty (might have other files)

        return count

    async def get_checkpoint_history(
        self, checkpoint_id: str, max_depth: int = 10
    ) -> list[Checkpoint]:
        """Get checkpoint history by following parent links."""
        history = []
        current_id = checkpoint_id

        for _ in range(max_depth):
            checkpoint = await self.load(current_id)
            if not checkpoint:
                break

            history.append(checkpoint)

            if not checkpoint.parent_checkpoint_id:
                break

            current_id = checkpoint.parent_checkpoint_id

        return history

    def get_stats(self) -> dict:
        """Get storage statistics."""
        stats = {
            "total_sessions": 0,
            "total_checkpoints": 0,
            "checkpoint_dir": str(self.checkpoint_dir),
            "disk_usage_bytes": 0,
        }

        for session_dir in self.checkpoint_dir.iterdir():
            if not session_dir.is_dir():
                continue

            stats["total_sessions"] += 1

            for checkpoint_file in session_dir.glob("*.json"):
                stats["total_checkpoints"] += 1
                stats["disk_usage_bytes"] += checkpoint_file.stat().st_size

        return stats
