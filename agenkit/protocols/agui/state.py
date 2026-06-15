"""State management for AG-UI Standard protocol.

This module provides state synchronization using JSON Patch (RFC 6902)
for efficient incremental updates between agents and frontends.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Optional

from agenkit.protocols.agui.events import StateDeltaEvent, StateSnapshotEvent


class StateManager:
    """Manages agent state with snapshot and delta tracking.

    This class maintains agent state and generates JSON Patch deltas
    for efficient state synchronization with frontends.

    JSON Patch (RFC 6902) operations:
    - add: Add a new value
    - remove: Remove a value
    - replace: Replace a value
    - move: Move a value
    - copy: Copy a value
    - test: Test that a value matches

    Example:
        ```python
        manager = StateManager()

        # Initialize state
        manager.set_state({"count": 0, "items": []})

        # Update state
        manager.update("count", 1)
        manager.update("items", ["apple"])

        # Get delta event
        delta_event = manager.get_delta_event()
        # Returns: StateDeltaEvent with JSON Patch operations

        # Get full snapshot
        snapshot_event = manager.get_snapshot_event()
        ```
    """

    def __init__(self, initial_state: Optional[dict[str, Any]] = None):
        """Initialize state manager.

        Args:
            initial_state: Optional initial state dict
        """
        self._state = initial_state or {}
        self._previous_state = deepcopy(self._state)
        self._pending_operations: list[dict[str, Any]] = []

    def set_state(self, state: dict[str, Any]) -> None:
        """Set the complete state.

        Args:
            state: New state dict
        """
        self._previous_state = deepcopy(self._state)
        self._state = deepcopy(state)
        self._pending_operations = []

    def get_state(self) -> dict[str, Any]:
        """Get current state.

        Returns:
            Current state dict
        """
        return deepcopy(self._state)

    def update(self, path: str, value: Any) -> None:
        """Update a value at a path.

        Args:
            path: JSON Pointer path (e.g., "/count", "/items/0")
            value: New value

        Example:
            ```python
            manager.update("/count", 5)
            manager.update("/user/name", "Alice")
            manager.update("/items/0", "apple")
            ```
        """
        # Parse path
        keys = self._parse_path(path)

        # Navigate to parent
        current = self._state
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Update value
        last_key = keys[-1]
        old_value = current.get(last_key)

        if old_value == value:
            return  # No change

        current[last_key] = value

        # Record operation
        if old_value is None:
            self._pending_operations.append({"op": "add", "path": path, "value": value})
        else:
            self._pending_operations.append({"op": "replace", "path": path, "value": value})

    def remove(self, path: str) -> None:
        """Remove a value at a path.

        Args:
            path: JSON Pointer path

        Example:
            ```python
            manager.remove("/items/0")
            manager.remove("/temp_data")
            ```
        """
        keys = self._parse_path(path)

        # Navigate to parent
        current = self._state
        for key in keys[:-1]:
            if key not in current:
                return  # Path doesn't exist
            current = current[key]

        # Remove value
        last_key = keys[-1]
        if last_key in current:
            del current[last_key]
            self._pending_operations.append({"op": "remove", "path": path})

    def get_delta_event(self) -> Optional[StateDeltaEvent]:
        """Get StateDelta event for pending changes.

        Returns:
            StateDeltaEvent if there are pending changes, None otherwise
        """
        if not self._pending_operations:
            return None

        event = StateDeltaEvent(delta=self._pending_operations.copy())
        self._pending_operations = []
        return event

    def get_snapshot_event(self) -> StateSnapshotEvent:
        """Get StateSnapshot event with full state.

        Returns:
            StateSnapshotEvent with current state
        """
        return StateSnapshotEvent(snapshot=self.get_state())

    def _parse_path(self, path: str) -> list[str]:
        """Parse JSON Pointer path.

        Args:
            path: JSON Pointer path (e.g., "/user/name", "/items/0")

        Returns:
            List of keys
        """
        if not path.startswith("/"):
            raise ValueError(f"Path must start with '/': {path}")

        if path == "/":
            return []

        # Remove leading slash and split
        return path[1:].split("/")

    def apply_patch(self, operations: list[dict[str, Any]]) -> None:
        """Apply JSON Patch operations to state.

        This is useful for applying changes from the frontend.

        Args:
            operations: List of JSON Patch operations

        Example:
            ```python
            manager.apply_patch([
                {"op": "replace", "path": "/count", "value": 10},
                {"op": "add", "path": "/items/-", "value": "banana"}
            ])
            ```
        """
        for op in operations:
            op_type = op["op"]
            path = op["path"]

            if op_type == "add" or op_type == "replace":
                self.update(path, op["value"])
            elif op_type == "remove":
                self.remove(path)
            # TODO: Implement move, copy, test operations if needed


__all__ = ["StateManager"]
