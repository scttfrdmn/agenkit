"""Tests for Model Context Protocol (MCP) implementation."""

import json

import pytest

from agenkit import Agent, Message
from agenkit.techniques.protocols.mcp import (
    AgentMCPServer,
    MCPAdapter,
    MCPMethod,
    MCPRequest,
    MCPResourceInfo,
    MCPServer,
    MCPToolInfo,
    ResourceRegistry,
    ToolRegistry,
    create_error_response,
    create_notification,
    create_request,
    create_response,
)

# ============================================================================
# Mock Classes
# ============================================================================


class MockAgent(Agent):
    """Mock agent for testing."""

    def __init__(self, agent_name: str = "mock-agent"):
        self._name = agent_name
        self._capabilities = ["test", "mock"]

    @property
    def name(self) -> str:
        """Agent name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Agent capabilities."""
        return self._capabilities

    async def process(self, message: Message) -> Message:
        """Echo the message back."""
        return Message(
            role="assistant", content=f"Processed: {message.content}", metadata={"processed": True}
        )


# ============================================================================
# Message Tests
# ============================================================================


@pytest.mark.asyncio
async def test_request_creation():
    """Test creating MCP request."""
    request = create_request(
        method=MCPMethod.RESOURCES_LIST, params={"filter": "test"}, request_id="req-1"
    )

    assert request.id == "req-1"
    assert request.method == MCPMethod.RESOURCES_LIST.value
    assert request.params == {"filter": "test"}
    assert request.jsonrpc == "2.0"


@pytest.mark.asyncio
async def test_request_serialization():
    """Test request to/from dict."""
    request = MCPRequest(id="req-1", method="resources/list", params={"key": "value"})

    # To dict
    data = request.to_dict()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "req-1"
    assert data["method"] == "resources/list"
    assert data["params"] == {"key": "value"}

    # From dict
    restored = MCPRequest.from_dict(data)
    assert restored.id == request.id
    assert restored.method == request.method
    assert restored.params == request.params


@pytest.mark.asyncio
async def test_response_creation():
    """Test creating MCP response."""
    response = create_response(request_id="req-1", result={"data": "test"})

    assert response.id == "req-1"
    assert response.result == {"data": "test"}
    assert response.error is None
    assert not response.is_error


@pytest.mark.asyncio
async def test_error_response_creation():
    """Test creating error response."""
    error_response = create_error_response(
        request_id="req-1", code=-32600, message="Invalid request"
    )

    assert error_response.id == "req-1"
    assert error_response.is_error
    assert error_response.error["code"] == -32600
    assert error_response.error["message"] == "Invalid request"


@pytest.mark.asyncio
async def test_notification_creation():
    """Test creating MCP notification."""
    notification = create_notification(method="notification/test", params={"event": "updated"})

    assert notification.method == "notification/test"
    assert notification.params == {"event": "updated"}
    assert notification.id is None  # Notifications have no ID


@pytest.mark.asyncio
async def test_response_json_serialization():
    """Test JSON serialization."""
    response = create_response(request_id="req-1", result={"test": True})

    json_str = response.to_json()
    parsed = json.loads(json_str)

    assert parsed["id"] == "req-1"
    assert parsed["result"]["test"] is True


# ============================================================================
# Resource Registry Tests
# ============================================================================


@pytest.mark.asyncio
async def test_resource_registry_register():
    """Test registering resources."""
    registry = ResourceRegistry()

    async def handler(params):
        return {"data": "test"}

    resource = registry.register(
        uri="test://resource",
        name="Test Resource",
        handler=handler,
        description="A test resource",
        mime_type="application/json",
    )

    assert resource.uri == "test://resource"
    assert resource.name == "Test Resource"
    assert registry.has_resource("test://resource")


@pytest.mark.asyncio
async def test_resource_registry_list():
    """Test listing resources."""
    registry = ResourceRegistry()

    async def handler1(params):
        return "data1"

    async def handler2(params):
        return "data2"

    registry.register("uri1", "Resource 1", handler1)
    registry.register("uri2", "Resource 2", handler2)

    resources = registry.list()
    assert len(resources) == 2

    # list() already returns MCPResourceInfo objects
    assert resources[0].uri == "uri1"
    assert resources[1].uri == "uri2"


@pytest.mark.asyncio
async def test_resource_fetch():
    """Test fetching resource data."""
    registry = ResourceRegistry()

    async def handler(params):
        user_id = params.get("user_id", "default")
        return {"user_id": user_id, "name": "John"}

    registry.register("user://profile", "User Profile", handler)

    # Fetch without params
    result = await registry.fetch("user://profile")
    assert result["user_id"] == "default"

    # Fetch with params
    result = await registry.fetch("user://profile", {"user_id": "123"})
    assert result["user_id"] == "123"


@pytest.mark.asyncio
async def test_resource_not_found():
    """Test fetching non-existent resource."""
    registry = ResourceRegistry()

    with pytest.raises(ValueError, match="Resource not found"):
        await registry.fetch("nonexistent://resource")


@pytest.mark.asyncio
async def test_resource_unregister():
    """Test unregistering resources."""
    registry = ResourceRegistry()

    async def handler(params):
        return "data"

    registry.register("test://resource", "Test", handler)
    assert registry.has_resource("test://resource")

    registry.unregister("test://resource")
    assert not registry.has_resource("test://resource")


# ============================================================================
# Tool Registry Tests
# ============================================================================


@pytest.mark.asyncio
async def test_tool_registry_register():
    """Test registering tools."""
    registry = ToolRegistry()

    async def handler(params):
        return {"result": params["x"] + params["y"]}

    schema = {
        "type": "object",
        "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
        "required": ["x", "y"],
    }

    tool = registry.register(
        name="add", description="Add two numbers", handler=handler, input_schema=schema
    )

    assert tool.name == "add"
    assert registry.has_tool("add")


@pytest.mark.asyncio
async def test_tool_execution():
    """Test executing tools."""
    registry = ToolRegistry()

    async def multiply(params):
        return {"result": params["x"] * params["y"]}

    schema = {
        "type": "object",
        "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
        "required": ["x", "y"],
    }

    registry.register("multiply", "Multiply numbers", multiply, schema)

    result = await registry.execute("multiply", {"x": 5, "y": 3})
    assert result["result"] == 15


@pytest.mark.asyncio
async def test_tool_validation():
    """Test tool parameter validation."""
    registry = ToolRegistry()

    async def handler(params):
        return {"result": "ok"}

    schema = {
        "type": "object",
        "properties": {"required_param": {"type": "string"}},
        "required": ["required_param"],
    }

    registry.register("test_tool", "Test", handler, schema)

    # Valid params
    result = await registry.execute("test_tool", {"required_param": "value"})
    assert result["result"] == "ok"

    # Invalid params (missing required field)
    with pytest.raises(ValueError, match="Invalid parameters"):
        await registry.execute("test_tool", {})


@pytest.mark.asyncio
async def test_tool_not_found():
    """Test executing non-existent tool."""
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="Tool not found"):
        await registry.execute("nonexistent", {})


@pytest.mark.asyncio
async def test_tool_list():
    """Test listing tools."""
    registry = ToolRegistry()

    async def handler1(params):
        return "result1"

    async def handler2(params):
        return "result2"

    registry.register("tool1", "Tool 1", handler1, {})
    registry.register("tool2", "Tool 2", handler2, {})

    tools = registry.list()
    assert len(tools) == 2

    # list() already returns MCPToolInfo objects
    assert tools[0].name == "tool1"
    assert tools[1].name == "tool2"


# ============================================================================
# MCP Server Tests
# ============================================================================


@pytest.mark.asyncio
async def test_server_creation():
    """Test creating MCP server."""
    server = MCPServer(
        name="test-server", version="1.0", capabilities={"resources": True, "tools": True}
    )

    assert server.name == "test-server"
    assert server.version == "1.0"
    assert server.capabilities["resources"] is True


@pytest.mark.asyncio
async def test_server_resource_decorator():
    """Test @server.resource decorator."""
    server = MCPServer(name="test")

    @server.resource(uri="test://data", name="Test Data", description="Test resource")
    async def get_data(params):
        return {"value": 42}

    assert server.resources.has_resource("test://data")

    # Fetch via server
    result = await server.resources.fetch("test://data")
    assert result["value"] == 42


@pytest.mark.asyncio
async def test_server_tool_decorator():
    """Test @server.tool decorator."""
    server = MCPServer(name="test")

    @server.tool(
        name="calculate",
        description="Calculate sum",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
    async def calculate(params):
        return {"sum": params["a"] + params["b"]}

    assert server.tools.has_tool("calculate")

    # Execute via server
    result = await server.tools.execute("calculate", {"a": 10, "b": 20})
    assert result["sum"] == 30


@pytest.mark.asyncio
async def test_server_handle_initialize():
    """Test handling initialize request."""
    server = MCPServer(name="test-server", version="1.0")

    request = create_request(
        method=MCPMethod.INITIALIZE, params={"protocolVersion": "1.0"}, request_id="req-1"
    )

    response = await server.handle_request(request)

    assert not response.is_error
    assert response.result["serverInfo"]["name"] == "test-server"
    assert response.result["serverInfo"]["version"] == "1.0"


@pytest.mark.asyncio
async def test_server_handle_resources_list():
    """Test handling resources/list request."""
    server = MCPServer(name="test")

    @server.resource("res1", "Resource 1")
    async def res1(params):
        return "data1"

    @server.resource("res2", "Resource 2")
    async def res2(params):
        return "data2"

    request = create_request(method=MCPMethod.RESOURCES_LIST, request_id="req-1")

    response = await server.handle_request(request)

    assert not response.is_error
    assert len(response.result["resources"]) == 2


@pytest.mark.asyncio
async def test_server_handle_resources_read():
    """Test handling resources/read request."""
    server = MCPServer(name="test")

    @server.resource("user://profile", "User Profile")
    async def profile(params):
        # Return a string for easier testing (dict would have text=None)
        return '{"name": "John", "email": "john@example.com"}'

    request = create_request(
        method=MCPMethod.RESOURCES_READ, params={"uri": "user://profile"}, request_id="req-1"
    )

    response = await server.handle_request(request)

    assert not response.is_error
    contents = response.result["contents"]
    assert len(contents) == 1
    assert "John" in contents[0]["text"]


@pytest.mark.asyncio
async def test_server_handle_tools_list():
    """Test handling tools/list request."""
    server = MCPServer(name="test")

    @server.tool("tool1", "Tool 1", {"type": "object"})
    async def tool1(params):
        return "result1"

    @server.tool("tool2", "Tool 2", {"type": "object"})
    async def tool2(params):
        return "result2"

    request = create_request(method=MCPMethod.TOOLS_LIST, request_id="req-1")

    response = await server.handle_request(request)

    assert not response.is_error
    assert len(response.result["tools"]) == 2


@pytest.mark.asyncio
async def test_server_handle_tools_call():
    """Test handling tools/call request."""
    server = MCPServer(name="test")

    @server.tool(
        name="greet",
        description="Greet someone",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    )
    async def greet(params):
        return f"Hello, {params['name']}!"

    request = create_request(
        method=MCPMethod.TOOLS_CALL,
        params={"name": "greet", "arguments": {"name": "Alice"}},
        request_id="req-1",
    )

    response = await server.handle_request(request)

    assert not response.is_error
    content = response.result["content"][0]["text"]
    assert "Hello, Alice!" in content


@pytest.mark.asyncio
async def test_server_error_handling():
    """Test server error handling."""
    server = MCPServer(name="test")

    # Test with invalid method
    request = create_request(method="invalid/method", request_id="req-1")

    response = await server.handle_request(request)

    assert response.is_error
    assert response.error["code"] == -32601  # Method not found


@pytest.mark.asyncio
async def test_server_info():
    """Test server info method."""
    server = MCPServer(name="test-server", version="2.0")

    info = server.info()

    assert info["name"] == "test-server"
    assert info["version"] == "2.0"
    assert "resources_count" in info
    assert "tools_count" in info
    assert info["resources_count"] == 0
    assert info["tools_count"] == 0


# ============================================================================
# Adapter Tests
# ============================================================================


@pytest.mark.asyncio
async def test_adapter_from_agent():
    """Test converting agent to MCP server."""
    agent = MockAgent(agent_name="my-agent")

    server = MCPAdapter.from_agent(agent, server_name="my-mcp-server")

    assert server.name == "my-mcp-server"
    assert server.tools.has_tool("process")

    # Test calling the agent via MCP
    result = await server.tools.execute("process", {"content": "Hello"})

    assert "Processed: Hello" in result["content"]
    assert result["metadata"]["processed"] is True


@pytest.mark.asyncio
async def test_adapter_agent_with_capabilities():
    """Test adapter with agent that has capabilities."""
    agent = MockAgent()

    server = MCPAdapter.from_agent(agent)

    # Should have capabilities resource
    assert server.resources.has_resource("agent://capabilities")

    # Fetch capabilities
    caps = await server.resources.fetch("agent://capabilities")
    assert caps["capabilities"] == ["test", "mock"]


@pytest.mark.asyncio
async def test_agent_mcp_server_wrapper():
    """Test AgentMCPServer convenience wrapper."""
    agent = MockAgent(agent_name="test-agent")

    wrapper = AgentMCPServer(agent, server_name="wrapped-server")

    assert wrapper.server.name == "wrapped-server"
    assert wrapper.agent is agent

    # Test info
    info = wrapper.info()
    assert info["name"] == "wrapped-server"


# ============================================================================
# Schema Tests
# ============================================================================


@pytest.mark.asyncio
async def test_mcp_resource_info():
    """Test MCPResourceInfo dataclass."""
    info = MCPResourceInfo(
        uri="test://resource",
        name="Test Resource",
        description="A test",
        mime_type="application/json",
        metadata={"key": "value"},
    )

    assert info.uri == "test://resource"
    assert info.name == "Test Resource"
    assert info.metadata["key"] == "value"


@pytest.mark.asyncio
async def test_mcp_tool_info():
    """Test MCPToolInfo dataclass."""
    schema = {"type": "object", "properties": {"x": {"type": "number"}}}

    info = MCPToolInfo(name="test_tool", description="A test tool", input_schema=schema)

    assert info.name == "test_tool"
    assert info.description == "A test tool"
    assert info.input_schema == schema


@pytest.mark.asyncio
async def test_mcp_method_enum():
    """Test MCPMethod enum values."""
    assert MCPMethod.INITIALIZE.value == "initialize"
    assert MCPMethod.RESOURCES_LIST.value == "resources/list"
    assert MCPMethod.RESOURCES_READ.value == "resources/read"
    assert MCPMethod.TOOLS_LIST.value == "tools/list"
    assert MCPMethod.TOOLS_CALL.value == "tools/call"


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_end_to_end_resource_flow():
    """Test complete resource flow from registration to fetch."""
    server = MCPServer(name="integration-test")

    # Register resource - return string for text content
    @server.resource(
        uri="data://users/123",
        name="User 123",
        description="User profile data",
        mime_type="application/json",
    )
    async def get_user(params):
        return "User: Alice (alice@example.com)"

    # Test list request
    list_request = create_request(method=MCPMethod.RESOURCES_LIST, request_id="list-1")
    list_response = await server.handle_request(list_request)
    assert len(list_response.result["resources"]) == 1

    # Test read request
    read_request = create_request(
        method=MCPMethod.RESOURCES_READ, params={"uri": "data://users/123"}, request_id="read-1"
    )
    read_response = await server.handle_request(read_request)
    assert not read_response.is_error

    content = read_response.result["contents"][0]["text"]
    assert "Alice" in content


@pytest.mark.asyncio
async def test_end_to_end_tool_flow():
    """Test complete tool flow from registration to execution."""
    server = MCPServer(name="integration-test")

    # Register tool - return string for text content
    @server.tool(
        name="search",
        description="Search for items",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "number"}},
            "required": ["query"],
        },
    )
    async def search(params):
        query = params["query"]
        params.get("limit", 10)
        return f"Search results for '{query}': Result 0, Result 1, Result 2"

    # Test list request
    list_request = create_request(method=MCPMethod.TOOLS_LIST, request_id="list-1")
    list_response = await server.handle_request(list_request)
    assert len(list_response.result["tools"]) == 1

    # Test call request
    call_request = create_request(
        method=MCPMethod.TOOLS_CALL,
        params={"name": "search", "arguments": {"query": "test", "limit": 5}},
        request_id="call-1",
    )
    call_response = await server.handle_request(call_request)
    assert not call_response.is_error

    result_text = call_response.result["content"][0]["text"]
    assert "test" in result_text


@pytest.mark.asyncio
async def test_end_to_end_agent_integration():
    """Test complete flow of agent as MCP server."""
    # Create agent
    agent = MockAgent(agent_name="integration-agent")

    # Convert to MCP server
    server = MCPAdapter.from_agent(agent, server_name="agent-server")

    # Initialize
    init_request = create_request(
        method=MCPMethod.INITIALIZE, params={"protocolVersion": "1.0"}, request_id="init-1"
    )
    init_response = await server.handle_request(init_request)
    assert not init_response.is_error

    # Call agent via tools/call
    call_request = create_request(
        method=MCPMethod.TOOLS_CALL,
        params={"name": "process", "arguments": {"content": "Test message"}},
        request_id="call-1",
    )
    call_response = await server.handle_request(call_request)
    assert not call_response.is_error

    # Result is a dict, so text will be None - check if content array is populated
    assert call_response.result["content"] is not None
    assert not call_response.result["isError"]


@pytest.mark.asyncio
async def test_multiple_resources_and_tools():
    """Test server with multiple resources and tools."""
    server = MCPServer(name="multi-test")

    # Register multiple resources
    @server.resource("data://resource1", "Resource 1")
    async def res1(params):
        return {"id": 1}

    @server.resource("data://resource2", "Resource 2")
    async def res2(params):
        return {"id": 2}

    @server.resource("data://resource3", "Resource 3")
    async def res3(params):
        return {"id": 3}

    # Register multiple tools
    @server.tool("tool1", "Tool 1", {"type": "object"})
    async def tool1(params):
        return "result1"

    @server.tool("tool2", "Tool 2", {"type": "object"})
    async def tool2(params):
        return "result2"

    # Verify counts
    assert len(server.resources.list()) == 3
    assert len(server.tools.list()) == 2

    # Test listing
    list_res_req = create_request(MCPMethod.RESOURCES_LIST, request_id="r1")
    list_res_resp = await server.handle_request(list_res_req)
    assert len(list_res_resp.result["resources"]) == 3

    list_tools_req = create_request(MCPMethod.TOOLS_LIST, request_id="t1")
    list_tools_resp = await server.handle_request(list_tools_req)
    assert len(list_tools_resp.result["tools"]) == 2
