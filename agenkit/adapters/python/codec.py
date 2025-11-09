"""Message serialization and deserialization for protocol adapter."""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agenkit.interfaces import Message, ToolResult

from .errors import InvalidMessageError, MalformedPayloadError, UnsupportedVersionError

PROTOCOL_VERSION = "1.0"


def encode_message(message: Message) -> dict[str, Any]:
    """Encode a Message object to a dictionary for JSON serialization.

    Args:
        message: The Message to encode

    Returns:
        Dictionary representation of the message
    """
    return {
        "role": message.role,
        "content": message.content,
        "metadata": message.metadata,
        "timestamp": message.timestamp.isoformat(),
    }


def decode_message(data: dict[str, Any]) -> Message:
    """Decode a dictionary to a Message object.

    Args:
        data: Dictionary representation of a message

    Returns:
        Decoded Message object

    Raises:
        MalformedPayloadError: If message data is invalid
    """
    try:
        return Message(
            role=data["role"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            # Parse timestamp if present, otherwise use current time
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else datetime.now(timezone.utc)
            ),
        )
    except (KeyError, ValueError, TypeError) as e:
        raise MalformedPayloadError(f"Failed to decode message: {e}", {"data": data}) from e


def encode_tool_result(result: ToolResult) -> dict[str, Any]:
    """Encode a ToolResult object to a dictionary for JSON serialization.

    Args:
        result: The ToolResult to encode

    Returns:
        Dictionary representation of the tool result
    """
    return {
        "success": result.success,
        "data": result.data,
        "error": result.error,
        "metadata": result.metadata,
    }


def decode_tool_result(data: dict[str, Any]) -> ToolResult:
    """Decode a dictionary to a ToolResult object.

    Args:
        data: Dictionary representation of a tool result

    Returns:
        Decoded ToolResult object

    Raises:
        MalformedPayloadError: If tool result data is invalid
    """
    try:
        return ToolResult(
            success=data["success"],
            data=data.get("data"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )
    except (KeyError, TypeError) as e:
        raise MalformedPayloadError(f"Failed to decode tool result: {e}", {"data": data}) from e


def create_request_envelope(
    method: str, agent_name: str | None = None, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create a protocol request envelope.

    Args:
        method: Method name ("process" or "execute")
        agent_name: Name of the target agent (for agent requests)
        payload: Request payload

    Returns:
        Request envelope dictionary
    """
    return {
        "version": PROTOCOL_VERSION,
        "type": "request",
        "id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "method": method,
            **({"agent_name": agent_name} if agent_name else {}),
            **(payload or {}),
        },
    }


def create_response_envelope(request_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a protocol response envelope.

    Args:
        request_id: ID of the request being responded to
        payload: Response payload

    Returns:
        Response envelope dictionary
    """
    return {
        "version": PROTOCOL_VERSION,
        "type": "response",
        "id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }


def create_error_envelope(
    request_id: str,
    error_code: str,
    error_message: str,
    error_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a protocol error envelope.

    Args:
        request_id: ID of the request that failed
        error_code: Error code
        error_message: Human-readable error message
        error_details: Additional error details

    Returns:
        Error envelope dictionary
    """
    return {
        "version": PROTOCOL_VERSION,
        "type": "error",
        "id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "error_code": error_code,
            "error_message": error_message,
            "error_details": error_details or {},
        },
    }


def create_stream_chunk_envelope(request_id: str, message: dict[str, Any]) -> dict[str, Any]:
    """Create a protocol stream chunk envelope.

    Args:
        request_id: ID of the streaming request
        message: Message chunk payload

    Returns:
        Stream chunk envelope dictionary
    """
    return {
        "version": PROTOCOL_VERSION,
        "type": "stream_chunk",
        "id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {"message": message},
    }


def create_stream_end_envelope(request_id: str) -> dict[str, Any]:
    """Create a protocol stream end envelope.

    Args:
        request_id: ID of the streaming request

    Returns:
        Stream end envelope dictionary
    """
    return {
        "version": PROTOCOL_VERSION,
        "type": "stream_end",
        "id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {},
    }


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Validate a protocol envelope.

    Args:
        envelope: Envelope to validate

    Raises:
        InvalidMessageError: If envelope is invalid
        UnsupportedVersionError: If protocol version is not supported
    """
    # Check required fields
    if "version" not in envelope:
        raise InvalidMessageError("Missing 'version' field in envelope")

    if envelope["version"] != PROTOCOL_VERSION:
        raise UnsupportedVersionError(
            f"Unsupported protocol version: {envelope['version']}", {"version": envelope["version"]}
        )

    if "type" not in envelope:
        raise InvalidMessageError("Missing 'type' field in envelope")

    valid_types = {
        "request",
        "response",
        "error",
        "heartbeat",
        "register",
        "unregister",
        "stream_chunk",
        "stream_end",
    }
    if envelope["type"] not in valid_types:
        raise InvalidMessageError(
            f"Invalid message type: {envelope['type']}", {"type": envelope["type"]}
        )

    if "id" not in envelope:
        raise InvalidMessageError("Missing 'id' field in envelope")

    if "payload" not in envelope:
        raise InvalidMessageError("Missing 'payload' field in envelope")


def encode_bytes(envelope: dict[str, Any]) -> bytes:
    """Encode an envelope to bytes for transmission.

    Args:
        envelope: Envelope dictionary to encode

    Returns:
        UTF-8 encoded JSON bytes
    """
    return json.dumps(envelope).encode("utf-8")


def decode_bytes(data: bytes) -> dict[str, Any]:
    """Decode bytes to an envelope dictionary.

    Args:
        data: UTF-8 encoded JSON bytes

    Returns:
        Envelope dictionary

    Raises:
        MalformedPayloadError: If data cannot be decoded
    """
    try:
        decoded_data: dict[str, Any] = json.loads(data.decode("utf-8"))
        validate_envelope(decoded_data)
        return decoded_data
    except json.JSONDecodeError as e:
        raise MalformedPayloadError(f"Failed to decode JSON: {e}") from e
    except UnicodeDecodeError as e:
        raise MalformedPayloadError(f"Failed to decode UTF-8: {e}") from e
