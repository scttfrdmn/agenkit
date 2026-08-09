"""Tool call tracking for AG-UI Standard protocol.

This module provides utilities for tracking and emitting tool call events
in the AG-UI protocol.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from agenkit.protocols.agui.events import (
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallProgressEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from agenkit import Tool


class ProgressReporter:
    """Helper for tools to report progress during execution.

    Example:
        ```python
        async def long_running_tool(reporter: ProgressReporter):
            for i in range(100):
                await process_item(i)
                reporter.report(i / 100, f"Processing item {i+1}/100")
        ```
    """

    def __init__(self, tool_call_id: str, callback: Callable):
        """Initialize progress reporter.

        Args:
            tool_call_id: The tool call ID
            callback: Callback to emit progress events
        """
        self._tool_call_id = tool_call_id
        self._callback = callback

    def report(
        self,
        progress: float,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Report progress.

        Args:
            progress: Progress percentage (0.0 to 1.0)
            status: Optional status message
            metadata: Optional additional metadata
        """
        self._callback(self._tool_call_id, progress, status, metadata)


class ToolCallTracker:
    """Tracks tool calls and emits AG-UI events.

    This class wraps tool execution to emit proper AG-UI tool call events:
    - ToolCallStart: Announces tool invocation
    - ToolCallArgs: Streams tool arguments (if large)
    - ToolCallEnd: Marks end of argument transmission
    - ToolCallResult: Provides tool execution result

    Example:
        ```python
        tracker = ToolCallTracker()

        # Track a tool call
        async for event in tracker.track_call(
            tool=SearchTool(),
            args={"query": "weather"},
            parent_message_id="msg-123"
        ):
            yield event
        ```
    """

    def __init__(self):
        """Initialize tool call tracker."""
        self._active_calls: dict[str, dict[str, Any]] = {}

    async def track_call(
        self,
        tool: Tool,
        args: dict[str, Any],
        parent_message_id: str | None = None,
        stream_args: bool = True,
        arg_chunk_size: int = 100,
        on_progress: Callable[[str, float, str | None], None] | None = None,
    ) -> AsyncIterator:
        """Track a tool call and emit events.

        Args:
            tool: The tool being called
            args: Tool arguments
            parent_message_id: Optional parent message ID
            stream_args: Whether to stream arguments in chunks
            arg_chunk_size: Characters per arg chunk
            on_progress: Optional callback for progress updates (tool_call_id, progress, status)

        Yields:
            AG-UI tool call events
        """
        # Generate tool call ID
        tool_call_id = f"tool-{uuid4()}"

        # Emit ToolCallStart
        yield ToolCallStartEvent(
            tool_call_id=tool_call_id,
            tool_call_name=tool.name,
            parent_message_id=parent_message_id,
        )

        # Serialize arguments
        args_json = json.dumps(args, separators=(",", ":"))

        # Stream arguments if large
        if stream_args and len(args_json) > arg_chunk_size:
            for i in range(0, len(args_json), arg_chunk_size):
                chunk = args_json[i : i + arg_chunk_size]
                yield ToolCallArgsEvent(
                    tool_call_id=tool_call_id,
                    delta=chunk,
                )
        else:
            # Send all args at once
            yield ToolCallArgsEvent(
                tool_call_id=tool_call_id,
                delta=args_json,
            )

        # Emit ToolCallEnd
        yield ToolCallEndEvent(tool_call_id=tool_call_id)

        # Execute tool with optional progress tracking
        try:
            # If progress callback provided, create progress reporter
            if on_progress:
                # Create progress event emitter
                progress_events = []

                def emit_progress(
                    tid: str,
                    progress: float,
                    status: str | None = None,
                    metadata: dict[str, Any] | None = None,
                ) -> None:
                    progress_events.append(
                        ToolCallProgressEvent(
                            tool_call_id=tid,
                            progress=progress,
                            status=status,
                            metadata=metadata,
                        )
                    )

                # Create reporter for tool to use
                reporter = ProgressReporter(tool_call_id, emit_progress)

                # Add reporter to args if tool accepts it
                if "progress_reporter" in tool.execute.__code__.co_varnames:
                    args["progress_reporter"] = reporter

            # Positional `params` dict, matching the Tool.execute() contract
            # declared in agenkit/interfaces.py:377. See #762.
            result = await tool.execute(args)

            # Emit any buffered progress events
            if on_progress and progress_events:
                for event in progress_events:
                    yield event

            # Generate message ID for result
            result_message_id = f"msg-{uuid4()}"

            # Emit ToolCallResult
            yield ToolCallResultEvent(
                message_id=result_message_id,
                tool_call_id=tool_call_id,
                content=result.data if result.success else result.error,
                role="tool",
            )

        except Exception as e:
            # Emit error result
            result_message_id = f"msg-{uuid4()}"
            yield ToolCallResultEvent(
                message_id=result_message_id,
                tool_call_id=tool_call_id,
                content={"error": str(e), "type": type(e).__name__},
                role="tool",
            )


class ToolRegistry:
    """Registry of available tools for AG-UI integration.

    This class maintains a registry of tools that can be advertised
    to frontends in AG-UI metadata.

    Example:
        ```python
        registry = ToolRegistry()
        registry.register(SearchTool())
        registry.register(CalculatorTool())

        # Get tool metadata for AG-UI
        tools_metadata = registry.get_metadata()
        # Returns: [{"name": "search", "description": "..."}, ...]
        ```
    """

    def __init__(self):
        """Initialize tool registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool.

        Args:
            tool: Tool to register
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def get_all(self) -> list[Tool]:
        """Get all registered tools.

        Returns:
            List of all tools
        """
        return list(self._tools.values())

    def get_metadata(self) -> list[dict[str, Any]]:
        """Get tool metadata for AG-UI.

        Returns:
            List of tool metadata dicts with name and description
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                # TODO: Add parameters schema if Tool interface supports it
            }
            for tool in self._tools.values()
        ]


__all__ = ["ProgressReporter", "ToolCallTracker", "ToolRegistry"]
