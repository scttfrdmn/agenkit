from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

DESCRIPTOR: _descriptor.FileDescriptor

class ResponseType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESPONSE_TYPE_UNSPECIFIED: _ClassVar[ResponseType]
    RESPONSE_TYPE_MESSAGE: _ClassVar[ResponseType]
    RESPONSE_TYPE_TOOL_RESULT: _ClassVar[ResponseType]
    RESPONSE_TYPE_ERROR: _ClassVar[ResponseType]

class ChunkType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CHUNK_TYPE_UNSPECIFIED: _ClassVar[ChunkType]
    CHUNK_TYPE_MESSAGE: _ClassVar[ChunkType]
    CHUNK_TYPE_END: _ClassVar[ChunkType]
    CHUNK_TYPE_ERROR: _ClassVar[ChunkType]

RESPONSE_TYPE_UNSPECIFIED: ResponseType
RESPONSE_TYPE_MESSAGE: ResponseType
RESPONSE_TYPE_TOOL_RESULT: ResponseType
RESPONSE_TYPE_ERROR: ResponseType
CHUNK_TYPE_UNSPECIFIED: ChunkType
CHUNK_TYPE_MESSAGE: ChunkType
CHUNK_TYPE_END: ChunkType
CHUNK_TYPE_ERROR: ChunkType

class Request(_message.Message):
    __slots__ = (
        "agent_name",
        "id",
        "messages",
        "metadata",
        "method",
        "timestamp",
        "tool_call",
        "version",
    )
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...

    VERSION_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    AGENT_NAME_FIELD_NUMBER: _ClassVar[int]
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALL_FIELD_NUMBER: _ClassVar[int]
    version: str
    id: str
    timestamp: str
    method: str
    agent_name: str
    messages: _containers.RepeatedCompositeFieldContainer[Message]
    metadata: _containers.ScalarMap[str, str]
    tool_call: ToolCall
    def __init__(
        self,
        version: str | None = ...,
        id: str | None = ...,
        timestamp: str | None = ...,
        method: str | None = ...,
        agent_name: str | None = ...,
        messages: _Iterable[Message | _Mapping] | None = ...,
        metadata: _Mapping[str, str] | None = ...,
        tool_call: ToolCall | _Mapping | None = ...,
    ) -> None: ...

class Response(_message.Message):
    __slots__ = (
        "error",
        "id",
        "message",
        "metadata",
        "timestamp",
        "tool_result",
        "type",
        "version",
    )
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...

    VERSION_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TOOL_RESULT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    version: str
    id: str
    timestamp: str
    type: ResponseType
    message: Message
    tool_result: ToolResult
    error: Error
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        version: str | None = ...,
        id: str | None = ...,
        timestamp: str | None = ...,
        type: ResponseType | str | None = ...,
        message: Message | _Mapping | None = ...,
        tool_result: ToolResult | _Mapping | None = ...,
        error: Error | _Mapping | None = ...,
        metadata: _Mapping[str, str] | None = ...,
    ) -> None: ...

class StreamChunk(_message.Message):
    __slots__ = ("error", "id", "message", "timestamp", "type", "version")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    version: str
    id: str
    timestamp: str
    type: ChunkType
    message: Message
    error: Error
    def __init__(
        self,
        version: str | None = ...,
        id: str | None = ...,
        timestamp: str | None = ...,
        type: ChunkType | str | None = ...,
        message: Message | _Mapping | None = ...,
        error: Error | _Mapping | None = ...,
    ) -> None: ...

class Message(_message.Message):
    __slots__ = ("content", "metadata", "role", "timestamp")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...

    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    role: str
    content: str
    metadata: _containers.ScalarMap[str, str]
    timestamp: str
    def __init__(
        self,
        role: str | None = ...,
        content: str | None = ...,
        metadata: _Mapping[str, str] | None = ...,
        timestamp: str | None = ...,
    ) -> None: ...

class ToolCall(_message.Message):
    __slots__ = ("arguments", "metadata", "name")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...

    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    name: str
    arguments: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        name: str | None = ...,
        arguments: str | None = ...,
        metadata: _Mapping[str, str] | None = ...,
    ) -> None: ...

class ToolResult(_message.Message):
    __slots__ = ("data", "error", "metadata", "success")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...

    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    success: bool
    data: str
    error: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        success: bool = ...,
        data: str | None = ...,
        error: str | None = ...,
        metadata: _Mapping[str, str] | None = ...,
    ) -> None: ...

class Error(_message.Message):
    __slots__ = ("code", "details", "message")
    class DetailsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: str | None = ..., value: str | None = ...) -> None: ...

    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    details: _containers.ScalarMap[str, str]
    def __init__(
        self,
        code: str | None = ...,
        message: str | None = ...,
        details: _Mapping[str, str] | None = ...,
    ) -> None: ...
