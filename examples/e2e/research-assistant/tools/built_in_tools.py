"""Built-in tools for research assistant.

Provides commonly-needed tools like search, calculator, document reader, etc.
"""

import re
from typing import List, Optional
from tools.tool_registry import Tool, ToolResult


# ============================================================================
# Search Tool
# ============================================================================


async def _search_function(query: str, num_results: int = 5) -> ToolResult:
    """
    Mock web search function.

    In production, replace with real search API (Google, Bing, Tavily, etc.)
    """
    # Mock search results
    mock_results = [
        {
            "title": f"Result about '{query}' - Article {i+1}",
            "url": f"https://example.com/article-{i+1}",
            "snippet": f"This article discusses {query} in detail. It covers various aspects including definitions, applications, and recent developments in the field.",
        }
        for i in range(min(num_results, 5))
    ]

    return ToolResult(
        success=True,
        output=mock_results,
        metadata={"query": query, "num_results": len(mock_results)},
    )


def SearchTool() -> Tool:
    """Create a web search tool."""
    return Tool(
        name="search",
        description="Search the web for information about a topic. Returns a list of relevant articles with titles, URLs, and snippets.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5, max 10)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        function=_search_function,
        cost=0.001,
        category="research",
    )


# ============================================================================
# Calculator Tool
# ============================================================================


async def _calculator_function(expression: str) -> ToolResult:
    """
    Safely evaluate mathematical expressions.

    Supports basic arithmetic, exponents, and common functions.
    """
    try:
        # Sanitize expression - only allow numbers, operators, and safe functions
        allowed_chars = set("0123456789+-*/().^ ")
        if not all(c in allowed_chars or c.isalpha() for c in expression):
            return ToolResult(
                success=False,
                output=None,
                error="Expression contains invalid characters",
            )

        # Replace ^ with **
        expression = expression.replace("^", "**")

        # Evaluate safely (in production, use a proper math parser)
        # This is simplified - use sympy or similar for production
        result = eval(
            expression,
            {"__builtins__": {}},
            {
                "abs": abs,
                "min": min,
                "max": max,
                "sum": sum,
                "round": round,
            },
        )

        return ToolResult(
            success=True,
            output=result,
            metadata={"expression": expression},
        )

    except Exception as e:
        return ToolResult(
            success=False,
            output=None,
            error=f"Failed to evaluate expression: {str(e)}",
        )


def CalculatorTool() -> Tool:
    """Create a calculator tool."""
    return Tool(
        name="calculator",
        description="Perform mathematical calculations. Supports basic arithmetic (+, -, *, /), exponents (^), and functions like abs, min, max.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10^3', 'max(5, 10)')",
                }
            },
            "required": ["expression"],
        },
        function=_calculator_function,
        cost=0.0001,
        category="utilities",
    )


# ============================================================================
# Document Reader Tool
# ============================================================================


async def _document_reader_function(url: str) -> ToolResult:
    """
    Mock document reader.

    In production, replace with real document fetching and parsing.
    """
    # Mock document content based on URL
    mock_content = f"""
# Document from {url}

This is a mock document that would be fetched from {url}.

## Key Points

1. Important concept A: Lorem ipsum dolor sit amet, consectetur adipiscing elit.
2. Important concept B: Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
3. Important concept C: Ut enim ad minim veniam, quis nostrud exercitation ullamco.

## Conclusion

This document provides comprehensive information about the topic. For more details,
refer to the full source at {url}.
    """.strip()

    return ToolResult(
        success=True,
        output=mock_content,
        metadata={"url": url, "length": len(mock_content)},
    )


def DocumentReaderTool() -> Tool:
    """Create a document reader tool."""
    return Tool(
        name="read_document",
        description="Fetch and read the content of a document from a URL. Returns the full text content.",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the document to read",
                }
            },
            "required": ["url"],
        },
        function=_document_reader_function,
        cost=0.002,
        category="research",
    )


# ============================================================================
# Note Taker Tool
# ============================================================================


class NoteTakerState:
    """Shared state for note taker."""

    def __init__(self):
        self.notes: List[str] = []


_note_taker_state = NoteTakerState()


async def _note_taker_function(
    action: str, content: Optional[str] = None, note_id: Optional[int] = None
) -> ToolResult:
    """
    Take and manage notes during research.

    Actions:
    - add: Add a new note
    - list: List all notes
    - get: Get a specific note by ID
    - clear: Clear all notes
    """
    global _note_taker_state

    if action == "add":
        if not content:
            return ToolResult(
                success=False,
                output=None,
                error="Content required for 'add' action",
            )

        _note_taker_state.notes.append(content)
        note_id = len(_note_taker_state.notes) - 1

        return ToolResult(
            success=True,
            output=f"Note added (ID: {note_id})",
            metadata={"note_id": note_id, "total_notes": len(_note_taker_state.notes)},
        )

    elif action == "list":
        if not _note_taker_state.notes:
            return ToolResult(
                success=True,
                output="No notes yet",
                metadata={"total_notes": 0},
            )

        notes_formatted = "\n".join(
            f"{i}. {note}" for i, note in enumerate(_note_taker_state.notes)
        )

        return ToolResult(
            success=True,
            output=notes_formatted,
            metadata={"total_notes": len(_note_taker_state.notes)},
        )

    elif action == "get":
        if note_id is None:
            return ToolResult(
                success=False,
                output=None,
                error="note_id required for 'get' action",
            )

        if note_id < 0 or note_id >= len(_note_taker_state.notes):
            return ToolResult(
                success=False,
                output=None,
                error=f"Invalid note_id: {note_id}",
            )

        return ToolResult(
            success=True,
            output=_note_taker_state.notes[note_id],
            metadata={"note_id": note_id},
        )

    elif action == "clear":
        count = len(_note_taker_state.notes)
        _note_taker_state.notes.clear()

        return ToolResult(
            success=True,
            output=f"Cleared {count} notes",
            metadata={"cleared_count": count},
        )

    else:
        return ToolResult(
            success=False,
            output=None,
            error=f"Unknown action: {action}. Use 'add', 'list', 'get', or 'clear'",
        )


def NoteTakerTool() -> Tool:
    """Create a note-taking tool."""
    return Tool(
        name="notes",
        description="Take and manage notes during research. Can add notes, list all notes, get specific notes, or clear all notes.",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "get", "clear"],
                    "description": "Action to perform: 'add' (add note), 'list' (show all), 'get' (retrieve specific), 'clear' (delete all)",
                },
                "content": {
                    "type": "string",
                    "description": "Note content (required for 'add' action)",
                },
                "note_id": {
                    "type": "integer",
                    "description": "Note ID (required for 'get' action)",
                },
            },
            "required": ["action"],
        },
        function=_note_taker_function,
        cost=0.0,
        category="utilities",
    )


# ============================================================================
# Tool Factory
# ============================================================================


def create_default_tools() -> List[Tool]:
    """
    Create the default set of tools for research assistant.

    Returns:
        List of Tool objects
    """
    return [
        SearchTool(),
        CalculatorTool(),
        DocumentReaderTool(),
        NoteTakerTool(),
    ]
