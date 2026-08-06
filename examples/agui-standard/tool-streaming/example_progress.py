"""Progress tracking example for long-running tools.

This example demonstrates:
- Progress reporting during tool execution
- Status updates with human-readable messages
- Frontend progress visualization
"""

import asyncio
from typing import Any, Optional

from agenkit import Agent, Message, Tool, ToolResult
from agenkit.protocols.agui import AGUIAdapter, ProgressReporter, ToolCallTracker


class FileProcessingTool(Tool):
    """Tool that simulates long-running file processing with progress."""

    @property
    def name(self) -> str:
        return "process_files"

    @property
    def description(self) -> str:
        return "Process multiple files with progress tracking"

    async def execute(self, **kwargs) -> ToolResult:
        """Process files with progress reporting."""
        file_count = kwargs.get("file_count", 10)
        progress_reporter: Optional[ProgressReporter] = kwargs.get("progress_reporter")

        processed_files = []

        for i in range(file_count):
            # Simulate processing
            await asyncio.sleep(0.3)

            processed_files.append(f"file_{i + 1}.txt")

            # Report progress if available
            if progress_reporter:
                progress_reporter.report(
                    progress=(i + 1) / file_count,
                    status=f"Processing file {i + 1}/{file_count}",
                    metadata={"current_file": f"file_{i + 1}.txt"},
                )

        return ToolResult(
            success=True,
            data={
                "files_processed": len(processed_files),
                "files": processed_files,
                "status": "complete",
            },
        )


class AnalysisTool(Tool):
    """Tool that simulates data analysis with progress."""

    @property
    def name(self) -> str:
        return "analyze_data"

    @property
    def description(self) -> str:
        return "Analyze dataset with progress tracking"

    async def execute(self, **kwargs) -> ToolResult:
        """Analyze data with progress reporting."""
        data_size = kwargs.get("data_size", 100)
        progress_reporter: Optional[ProgressReporter] = kwargs.get("progress_reporter")

        results = {"analyzed": 0, "insights": []}

        # Phase 1: Data loading (0-20%)
        if progress_reporter:
            progress_reporter.report(0.1, "Loading data...")
        await asyncio.sleep(0.5)

        # Phase 2: Analysis (20-80%)
        steps = 10
        for i in range(steps):
            await asyncio.sleep(0.2)

            if progress_reporter:
                progress = 0.2 + (0.6 * (i + 1) / steps)
                progress_reporter.report(
                    progress=progress,
                    status=f"Analyzing batch {i + 1}/{steps}",
                    metadata={"phase": "analysis", "batch": i + 1},
                )

            results["analyzed"] += data_size // steps

        # Phase 3: Generating insights (80-100%)
        if progress_reporter:
            progress_reporter.report(0.9, "Generating insights...")
        await asyncio.sleep(0.5)

        results["insights"] = [
            "Pattern A detected",
            "Anomaly at position 47",
            "Trend: increasing",
        ]

        if progress_reporter:
            progress_reporter.report(1.0, "Analysis complete")

        return ToolResult(
            success=True,
            data=results,
        )


class ProcessingAgent(Agent):
    """Agent with progress-reporting tools."""

    def __init__(self):
        self._file_tool = FileProcessingTool()
        self._analysis_tool = AnalysisTool()
        self._tracker = ToolCallTracker()

    @property
    def name(self) -> str:
        return "ProcessingAgent"

    async def process(self, message: Message) -> Message:
        """Process message with progress-tracked tool calls."""
        content = message.content.lower()

        if "file" in content:
            # Use file processing tool
            response_parts = ["🔧 Starting file processing..."]

            async for event in self._tracker.track_call(
                tool=self._file_tool,
                args={"file_count": 5},
                stream_args=False,
                on_progress=True,
            ):
                if event.type == "tool_call_progress":
                    percentage = int(event.progress * 100)
                    response_parts.append(
                        f"📊 Progress: {percentage}% - {event.status or 'Processing...'}"
                    )
                elif event.type == "tool_call_result":
                    result = event.content
                    response_parts.append(
                        f"✅ Complete! Processed {result['files_processed']} files"
                    )

            return Message(role="assistant", content="\n".join(response_parts))

        elif "analyze" in content:
            # Use analysis tool
            response_parts = ["🔬 Starting data analysis..."]

            async for event in self._tracker.track_call(
                tool=self._analysis_tool,
                args={"data_size": 1000},
                stream_args=False,
                on_progress=True,
            ):
                if event.type == "tool_call_progress":
                    percentage = int(event.progress * 100)
                    response_parts.append(
                        f"📊 Progress: {percentage}% - {event.status or 'Analyzing...'}"
                    )
                elif event.type == "tool_call_result":
                    result = event.content
                    response_parts.append(f"✅ Analyzed {result['analyzed']} records")
                    response_parts.append(f"📈 Insights: {', '.join(result['insights'])}")

            return Message(role="assistant", content="\n".join(response_parts))

        else:
            return Message(
                role="assistant",
                content=(
                    "I can help with:\n"
                    "  • 'process files' - Process multiple files\n"
                    "  • 'analyze data' - Analyze dataset\n\n"
                    "Both operations show progress updates!"
                ),
            )


async def main():
    """Run progress tracking example."""
    print("=" * 60)
    print("Progress Tracking Example")
    print("=" * 60)
    print()

    # Create agent and adapter
    agent = ProcessingAgent()
    adapter = AGUIAdapter(agent, chunk_size=40)

    # Scenario 1: File processing with progress
    print("Scenario 1: File Processing")
    print("-" * 60)

    async for event in adapter.stream_events(
        message=Message(role="user", content="process files"),
        thread_id="progress-1",
    ):
        if event.type == "tool_call_start":
            print(f"🔧 {event.tool_call_name}")

        elif event.type == "tool_call_progress":
            percentage = int(event.progress * 100)
            bar = "█" * (percentage // 5) + "░" * (20 - percentage // 5)
            print(f"  [{bar}] {percentage}% - {event.status or ''}")

        elif event.type == "tool_call_result":
            print(f"  ✅ Result: {event.content}")

        elif event.type == "text_message_content":
            print(event.delta, end="", flush=True)

    print("\n\n")

    # Scenario 2: Data analysis with progress
    print("Scenario 2: Data Analysis")
    print("-" * 60)

    async for event in adapter.stream_events(
        message=Message(role="user", content="analyze data"),
        thread_id="progress-2",
    ):
        if event.type == "tool_call_start":
            print(f"🔬 {event.tool_call_name}")

        elif event.type == "tool_call_progress":
            percentage = int(event.progress * 100)
            bar = "█" * (percentage // 5) + "░" * (20 - percentage // 5)
            metadata_str = ""
            if event.metadata:
                metadata_str = f" ({event.metadata.get('phase', '')})"
            print(f"  [{bar}] {percentage}%{metadata_str} - {event.status or ''}")

        elif event.type == "tool_call_result":
            print(f"  ✅ Complete!")

        elif event.type == "text_message_content":
            print(event.delta, end="", flush=True)

    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
