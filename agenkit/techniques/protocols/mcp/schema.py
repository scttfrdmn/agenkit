"""
MCP Schema Definitions and Utilities.

Defines JSON schemas for MCP protocol messages and validation utilities.

References:
    - MCP Specification: https://modelcontextprotocol.io/
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MCPMessageType(Enum):
    """MCP message types."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPMethod(Enum):
    """Standard MCP methods."""

    # Resource methods
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"

    # Tool methods
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # Initialization
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"

    # Prompts (optional)
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"


@dataclass
class MCPResourceInfo:
    """Information about an MCP resource."""

    uri: str
    name: str
    description: str | None = None
    mime_type: str | None = "text/plain"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPToolInfo:
    """Information about an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPPromptInfo:
    """Information about an MCP prompt."""

    name: str
    description: str
    arguments: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_json_schema(data: dict[str, Any], schema: dict[str, Any]) -> bool:
    """
    Validate data against JSON schema.

    Args:
        data: Data to validate
        schema: JSON schema

    Returns:
        True if valid, False otherwise

    Note:
        This is a simple validation. For production, use jsonschema library.
    """
    # Simple type validation
    if "type" in schema:
        expected_type = schema["type"]

        if (
            (expected_type == "object" and not isinstance(data, dict))
            or (expected_type == "array" and not isinstance(data, list))
            or (expected_type == "string" and not isinstance(data, str))
            or (expected_type == "number" and not isinstance(data, (int, float)))
            or (expected_type == "boolean" and not isinstance(data, bool))
        ):
            return False

    # Validate required properties
    if "required" in schema and isinstance(data, dict):
        for prop in schema["required"]:
            if prop not in data:
                return False

    return True


def create_tool_schema(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """
    Create JSON schema for a tool.

    Args:
        name: Tool name
        description: Tool description
        parameters: Parameter definitions

    Returns:
        Tool schema

    Example:
        >>> schema = create_tool_schema(
        ...     name="search",
        ...     description="Search the web",
        ...     parameters={
        ...         "query": {"type": "string", "description": "Search query"},
        ...         "limit": {"type": "number", "description": "Max results"}
        ...     }
        ... )
    """
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": [k for k, v in parameters.items() if v.get("required", False)],
            },
        },
    }


def create_resource_schema(
    uri: str, name: str, description: str, mime_type: str = "text/plain"
) -> dict[str, Any]:
    """
    Create schema for a resource.

    Args:
        uri: Resource URI
        name: Resource name
        description: Resource description
        mime_type: MIME type

    Returns:
        Resource schema
    """
    return {"uri": uri, "name": name, "description": description, "mimeType": mime_type}
