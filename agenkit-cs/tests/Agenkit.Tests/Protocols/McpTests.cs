using System.Text.Json;
using Agenkit.Core;
using Agenkit.Protocols.Mcp;

namespace Agenkit.Tests.Protocols;

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

/// <summary>
/// Minimal in-memory MCP client used to drive adapter tests without a real process.
/// </summary>
internal sealed class MockMcpClient : IMcpClient
{
    private readonly IReadOnlyList<McpTool> _tools;
    private readonly McpToolResult _fixedResult;

    public MockMcpClient(IReadOnlyList<McpTool> tools, McpToolResult fixedResult)
    {
        _tools = tools;
        _fixedResult = fixedResult;
    }

    public McpServerInfo ServerInfo => new("mock-server", "1.0.0");

    public Task InitializeAsync(CancellationToken ct = default) => Task.CompletedTask;

    public Task<IReadOnlyList<McpTool>> ListToolsAsync(CancellationToken ct = default) =>
        Task.FromResult(_tools);

    public Task<McpToolResult> CallToolAsync(string name, IDictionary<string, object> args, CancellationToken ct = default) =>
        Task.FromResult(_fixedResult);

    public void Dispose() { }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

public class McpTests
{
    // 1. JsonRpcRequest serialises to expected JSON keys
    [Fact]
    public void JsonRpcRequest_SerializesCorrectly()
    {
        var req = new JsonRpcRequest("2.0", 1L, "tools/list", null);
        var json = JsonSerializer.Serialize(req);
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        root.GetProperty("jsonrpc").GetString().Should().Be("2.0");
        root.GetProperty("id").GetInt64().Should().Be(1L);
        root.GetProperty("method").GetString().Should().Be("tools/list");
    }

    // 2. JsonRpcResponse deserialises from JSON string
    [Fact]
    public void JsonRpcResponse_DeserializesCorrectly()
    {
        const string json = """{"jsonrpc":"2.0","id":42,"result":null,"error":null}""";
        var resp = JsonSerializer.Deserialize<JsonRpcResponse>(json);
        resp.Should().NotBeNull();
        resp!.Jsonrpc.Should().Be("2.0");
        resp.Id.Should().Be(42L);
        resp.Error.Should().BeNull();
    }

    // 3. McpTool round-trips JSON
    [Fact]
    public void McpTool_RoundTripsJson()
    {
        var tool = new McpTool("calculator", "does math");
        var json = JsonSerializer.Serialize(tool);
        var restored = JsonSerializer.Deserialize<McpTool>(json);
        restored.Should().NotBeNull();
        restored!.Name.Should().Be("calculator");
        restored.Description.Should().Be("does math");
    }

    // 4. TextContent joins a single block
    [Fact]
    public void TextContent_JoinsSingleBlock()
    {
        var contents = new[] { new McpContent("text", "hello") };
        contents.TextContent().Should().Be("hello");
    }

    // 5. TextContent joins multiple blocks
    [Fact]
    public void TextContent_JoinsMultipleBlocks()
    {
        var contents = new[]
        {
            new McpContent("text", "hello"),
            new McpContent("text", "world"),
        };
        contents.TextContent().Should().Be("hello world");
    }

    // 6. StdioClient implements IMcpClient (compile-time check)
    [Fact]
    public void StdioClient_ImplementsIMcpClient()
    {
        IMcpClient client = new StdioClient("echo");
        client.Should().NotBeNull();
        client.Dispose();
    }

    // 7. McpHttpClient implements IMcpClient (compile-time check)
    [Fact]
    public void McpHttpClient_ImplementsIMcpClient()
    {
        IMcpClient client = new McpHttpClient("http://localhost:9999");
        client.Should().NotBeNull();
        client.Dispose();
    }

    // 8. McpToolAdapter.Name returns McpTool.Name
    [Fact]
    public async Task Adapter_Name_ReturnsMcpToolName()
    {
        var mcpTool = new McpTool("my-tool", "desc");
        var mock = new MockMcpClient([mcpTool], new McpToolResult([], false));
        var tools = await mock.ToolsFromClientAsync();
        tools[0].Name.Should().Be("my-tool");
    }

    // 9. McpToolAdapter.Description returns McpTool.Description
    [Fact]
    public async Task Adapter_Description_ReturnsMcpToolDescription()
    {
        var mcpTool = new McpTool("my-tool", "does something useful");
        var mock = new MockMcpClient([mcpTool], new McpToolResult([], false));
        var tools = await mock.ToolsFromClientAsync();
        tools[0].Description.Should().Be("does something useful");
    }

    // 10. Adapter execute success (isError=false → ToolResult.Ok)
    [Fact]
    public async Task Adapter_Execute_Success_ReturnsOkResult()
    {
        var mcpTool = new McpTool("greeter", "says hello");
        var fixedResult = new McpToolResult([new McpContent("text", "hello!")], IsError: false);
        var mock = new MockMcpClient([mcpTool], fixedResult);
        var tools = await mock.ToolsFromClientAsync();
        var result = await tools[0].ExecuteAsync(new Dictionary<string, object>());
        result.Success.Should().BeTrue();
        result.Data.Should().Be("hello!");
    }

    // 11. Adapter execute isError=true → ToolResult.Fail
    [Fact]
    public async Task Adapter_Execute_IsError_ReturnsFailResult()
    {
        var mcpTool = new McpTool("broken", "always fails");
        var fixedResult = new McpToolResult([new McpContent("text", "something went wrong")], IsError: true);
        var mock = new MockMcpClient([mcpTool], fixedResult);
        var tools = await mock.ToolsFromClientAsync();
        var result = await tools[0].ExecuteAsync(new Dictionary<string, object>());
        result.Success.Should().BeFalse();
        result.Error.Should().Be("something went wrong");
    }

    // 12. ToolsFromClientAsync wraps all tools returned by ListToolsAsync
    [Fact]
    public async Task ToolsFromClientAsync_WrapsAllTools()
    {
        var mcpTools = new[]
        {
            new McpTool("tool-a", "desc a"),
            new McpTool("tool-b", "desc b"),
            new McpTool("tool-c", "desc c"),
        };
        var mock = new MockMcpClient(mcpTools, new McpToolResult([], false));
        var tools = await mock.ToolsFromClientAsync();
        tools.Should().HaveCount(3);
        tools.Select(t => t.Name).Should().BeEquivalentTo("tool-a", "tool-b", "tool-c");
    }
}
