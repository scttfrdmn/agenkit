# Model Context Protocol (MCP)

The Model Context Protocol (MCP) is Anthropic's open standard for connecting AI assistants to external data sources and tools. Agenkit provides a complete implementation of MCP, enabling seamless integration between Agenkit agents and Claude Desktop or other MCP-compatible clients.

## Overview

MCP allows AI assistants to access:
- **Resources**: Data sources identified by URIs (e.g., `user://profile`, `file://doc.txt`)
- **Tools**: Actions with typed parameters (e.g., search, calculate, format)
- **Prompts**: Templated prompts for specific tasks

Agenkit's MCP implementation supports:
- ✅ MCP Server (expose resources and tools)
- ✅ MCP Client (connect to MCP servers)
- ✅ Multiple transports (stdio, HTTP, SSE)
- ✅ Agenkit Agent integration
- ✅ JSON-RPC 2.0 protocol
- ✅ Full specification compliance

## Quick Start

### Expose an Agent via MCP

```python
from agenkit import Agent, Message
from agenkit.techniques.protocols.mcp import AgentMCPServer

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my_agent"

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=f"Processed: {message.content}"
        )

# Wrap agent as MCP server
agent = MyAgent()
wrapper = AgentMCPServer(agent)

# Run for Claude Desktop (stdio)
await wrapper.run(transport="stdio")
```

### Create an MCP Server

```python
from agenkit.techniques.protocols.mcp import MCPServer

server = MCPServer(name="my-server", version="1.0")

# Register a resource
@server.resource(
    uri="user://profile",
    name="User Profile",
    description="Get user profile data"
)
async def get_profile(params):
    return {"name": "John", "email": "john@example.com"}

# Register a tool
@server.tool(
    name="search",
    description="Search for items",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"]
    }
)
async def search(params):
    query = params["query"]
    return f"Results for: {query}"

# Start server
await server.start(transport="http", port=3000)
```

### Connect with MCP Client

```python
from agenkit.techniques.protocols.mcp import MCPClient

client = MCPClient(server_url="http://localhost:3000/mcp")

# Initialize connection
await client.initialize()

# List resources
resources = await client.list_resources()

# Read resource
data = await client.get_resource("user://profile")

# List tools
tools = await client.list_tools()

# Call tool
result = await client.call_tool("search", query="AI agents")
```

## Core Concepts

### Resources

Resources are data sources identified by URIs. They can return text, JSON, or binary data.

**Resource URI Schemes:**
- `user://` - User-specific data
- `file://` - File system access
- `db://` - Database queries
- `api://` - External API access
- `config://` - Configuration settings
- Custom schemes for domain-specific data

**Example:**
```python
@server.resource(
    uri="db://users/123",
    name="User 123",
    description="User profile from database",
    mime_type="application/json"
)
async def get_user(params):
    user_id = params.get("user_id", "123")
    return await database.get_user(user_id)
```

### Tools

Tools are actions with typed parameters defined by JSON schemas. They enable agents to perform operations.

**Example:**
```python
@server.tool(
    name="calculate",
    description="Perform mathematical calculations",
    input_schema={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression to evaluate"
            }
        },
        "required": ["expression"]
    }
)
async def calculate(params):
    expression = params["expression"]
    result = eval(expression, {"__builtins__": {}}, {})
    return {"expression": expression, "result": result}
```

### Transports

MCP supports multiple transport layers:

| Transport | Use Case | Connection Type |
|-----------|----------|----------------|
| **stdio** | Claude Desktop | stdin/stdout |
| **HTTP** | Web services | HTTP POST |
| **SSE** | Streaming | Server-Sent Events |

**Stdio (Claude Desktop):**
```python
await server.start(transport="stdio")
```

**HTTP:**
```python
await server.start(transport="http", host="localhost", port=3000)
```

**SSE:**
```python
await server.start(transport="sse", host="localhost", port=3000)
```

## Claude Desktop Integration

### 1. Create MCP Server Script

Create a Python script that runs your agent as an MCP server:

```python
#!/usr/bin/env python3
import asyncio
from agenkit.techniques.protocols.mcp import MCPServer

async def main():
    server = MCPServer(name="my-agent")

    @server.tool("process", "Process message", {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]})
    async def process(params):
        return f"Processed: {params['content']}"

    await server.start(transport="stdio")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Configure Claude Desktop

Add to `~/.config/Claude/claude_desktop_config.json` (Mac/Linux) or `%APPDATA%/Claude/claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "my-agent": {
      "command": "python",
      "args": ["/absolute/path/to/your_script.py"]
    }
  }
}
```

### 3. Restart Claude Desktop

Restart Claude Desktop. Your agent will now be available as an MCP server.

### 4. Use in Claude

In Claude Desktop, you can now say:
> "Use the my-agent server to process this message: Hello World"

Claude will automatically call your MCP server's tools.

## Advanced Usage

### Exposing ReAct Agents

```python
from agenkit.patterns import ReActAgent
from agenkit.techniques.protocols.mcp import MCPAdapter

# Create ReAct agent with tools
react_agent = ReActAgent(
    llm=my_llm,
    tools=[search_tool, calculator_tool],
    max_iterations=5
)

# Convert to MCP server
server = MCPAdapter.from_agent(
    agent=react_agent,
    server_name="react-agent-server"
)

# Start server
await server.start(transport="stdio")
```

### Using MCP Tools in Agenkit

```python
from agenkit.techniques.protocols.mcp import MCPAdapter, MCPClient
from agenkit.patterns import ReActAgent

# Connect to external MCP server
client = MCPClient("http://external-mcp-server/mcp")
await client.initialize()

# Convert MCP tool to Agenkit tool
search_tool = MCPAdapter.to_tool(
    client=client,
    tool_name="search",
    description="Search the web"
)

# Use in ReAct agent
agent = ReActAgent(llm=my_llm, tools=[search_tool])
```

### Resource Caching

For expensive resources, implement caching:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
async def fetch_expensive_data(key):
    # Expensive computation or API call
    return await database.complex_query(key)

@server.resource("data://cached", "Cached Data")
async def get_cached_data(params):
    key = params.get("key", "default")
    return await fetch_expensive_data(key)
```

### Error Handling

```python
@server.tool(
    name="risky_operation",
    description="Operation that might fail",
    input_schema={...}
)
async def risky_operation(params):
    try:
        result = await perform_operation(params)
        return {"success": True, "data": result}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        # MCP will convert exceptions to error responses
        raise
```

### Authentication

For HTTP/SSE transports:

```python
# Server side: implement auth middleware
# (depends on your HTTP framework)

# Client side: pass auth headers
client = MCPClient(
    server_url="http://localhost:3000/mcp",
    auth={"Authorization": "Bearer YOUR_TOKEN"}
)
```

## Protocol Details

### JSON-RPC 2.0

MCP uses JSON-RPC 2.0 for message format:

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {"query": "AI"}
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "content": [
      {"type": "text", "text": "Results: ..."}
    ]
  }
}
```

**Error:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "error": {
    "code": -32600,
    "message": "Invalid request"
  }
}
```

### MCP Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `initialize` | Initialize connection | `protocolVersion` |
| `resources/list` | List available resources | - |
| `resources/read` | Read resource data | `uri`, params |
| `tools/list` | List available tools | - |
| `tools/call` | Execute a tool | `name`, `arguments` |

### Error Codes

| Code | Meaning |
|------|---------|
| -32700 | Parse error |
| -32600 | Invalid request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |

## Examples

See the `examples/techniques/protocols/mcp/` directory for complete examples:

1. **`claude_desktop_demo.py`** - Complete Claude Desktop integration with resources and tools
2. **`http_server_example.py`** - HTTP server with system tools and monitoring
3. **`agent_server_example.py`** - Exposing Agenkit agents via MCP (with CLI options)
4. **`client_example.py`** - MCP client with interactive mode

## Testing

Run MCP tests:

```bash
pytest tests/techniques/protocols/test_mcp.py -v
```

Test coverage includes:
- Message serialization/deserialization
- Resource and tool registration
- Server request handling
- All transport layers
- Client operations
- Agenkit adapter functionality
- End-to-end integration scenarios

## Best Practices

### 1. Resource Design

- Use descriptive URIs with clear schemes
- Include metadata for resource discovery
- Return appropriate MIME types
- Handle missing or invalid parameters gracefully

### 2. Tool Design

- Provide detailed input schemas with descriptions
- Validate parameters before processing
- Return structured data when possible
- Include error information in results

### 3. Transport Selection

| Scenario | Recommended Transport |
|----------|----------------------|
| Claude Desktop integration | stdio |
| Web services / REST API | HTTP |
| Streaming / real-time updates | SSE |
| Local development | HTTP |

### 4. Error Handling

- Use try/except blocks in handlers
- Return structured error information
- Log errors for debugging
- Don't expose sensitive information in error messages

### 5. Performance

- Cache expensive resources
- Use async/await throughout
- Limit resource sizes (consider pagination)
- Set appropriate timeouts

## Troubleshooting

### Claude Desktop not connecting

1. Check config file path:
   - Mac/Linux: `~/.config/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%/Claude/claude_desktop_config.json`
2. Verify absolute paths in config
3. Check logs in Claude Desktop console
4. Test script independently with `python your_script.py`

### HTTP connection errors

```bash
# Test server is running
curl -X POST http://localhost:3000/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}'
```

### Tool execution failures

- Check input schema matches parameters
- Verify tool is registered: `await client.list_tools()`
- Check tool handler doesn't raise unhandled exceptions
- Review parameter validation logic

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/mcp)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [Agenkit MCP API Reference](/api/techniques/protocols/mcp)

## Architecture

### MCP Stack

```
┌─────────────────────────────────────────┐
│         Claude Desktop / Client         │
└─────────────────────────────────────────┘
                    │
         ┌──────────┴──────────┐
         │   Transport Layer   │
         │ (stdio/HTTP/SSE)    │
         └──────────┬──────────┘
                    │
         ┌──────────┴──────────┐
         │   JSON-RPC 2.0     │
         │   Message Layer     │
         └──────────┬──────────┘
                    │
         ┌──────────┴──────────┐
         │    MCP Server       │
         │  ┌─────────────┐   │
         │  │ Resources   │   │
         │  └─────────────┘   │
         │  ┌─────────────┐   │
         │  │   Tools     │   │
         │  └─────────────┘   │
         └──────────┬──────────┘
                    │
         ┌──────────┴──────────┐
         │   Agenkit Agent     │
         │   (Optional)        │
         └─────────────────────┘
```

### Component Responsibilities

- **Transport**: Handle I/O (stdin/stdout, HTTP requests, SSE)
- **Message Layer**: Parse/serialize JSON-RPC messages
- **Server**: Route requests to resources/tools
- **Registry**: Manage registered resources and tools
- **Adapter**: Bridge between Agenkit and MCP

## Implementation Stats

- **Total Code**: ~1,850 LOC
- **Core Implementation**: 9 files, ~1,550 LOC
- **Tests**: 36 tests, 100% pass rate
- **Examples**: 4 examples, ~1,200 LOC
- **Transport Support**: stdio, HTTP, SSE
- **MCP Version**: 1.0
- **JSON-RPC Version**: 2.0

## License

Agenkit's MCP implementation is open source under the MIT License.

## Contributing

Contributions welcome! Areas for enhancement:
- Additional transport types (WebSocket, gRPC)
- Enhanced authentication/authorization
- Rate limiting and quota management
- Prompt support (currently resources and tools only)
- Connection pooling for clients
- Metrics and monitoring
