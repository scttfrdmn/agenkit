from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

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
    __slots__ = ("version", "id", "timestamp", "method", "agent_name", "messages", "metadata", "tool_call")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
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
    def __init__(self, version: _Optional[str] = ..., id: _Optional[str] = ..., timestamp: _Optional[str] = ..., method: _Optional[str] = ..., agent_name: _Optional[str] = ..., messages: _Optional[_Iterable[_Union[Message, _Mapping]]] = ..., metadata: _Optional[_Mapping[str, str]] = ..., tool_call: _Optional[_Union[ToolCall, _Mapping]] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ("version", "id", "timestamp", "type", "message", "tool_result", "error", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
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
    def __init__(self, version: _Optional[str] = ..., id: _Optional[str] = ..., timestamp: _Optional[str] = ..., type: _Optional[_Union[ResponseType, str]] = ..., message: _Optional[_Union[Message, _Mapping]] = ..., tool_result: _Optional[_Union[ToolResult, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class StreamChunk(_message.Message):
    __slots__ = ("version", "id", "timestamp", "type", "message", "error")
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
    def __init__(self, version: _Optional[str] = ..., id: _Optional[str] = ..., timestamp: _Optional[str] = ..., type: _Optional[_Union[ChunkType, str]] = ..., message: _Optional[_Union[Message, _Mapping]] = ..., error: _Optional[_Union[Error, _Mapping]] = ...) -> None: ...

class Message(_message.Message):
    __slots__ = ("role", "content", "metadata", "timestamp")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    role: str
    content: str
    metadata: _containers.ScalarMap[str, str]
    timestamp: str
    def __init__(self, role: _Optional[str] = ..., content: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ..., timestamp: _Optional[str] = ...) -> None: ...

class ToolCall(_message.Message):
    __slots__ = ("name", "arguments", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    name: str
    arguments: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, name: _Optional[str] = ..., arguments: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ToolResult(_message.Message):
    __slots__ = ("success", "data", "error", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    success: bool
    data: str
    error: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, success: bool = ..., data: _Optional[str] = ..., error: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Error(_message.Message):
    __slots__ = ("code", "message", "details")
    class DetailsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    details: _containers.ScalarMap[str, str]
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ..., details: _Optional[_Mapping[str, str]] = ...) -> None: ...
