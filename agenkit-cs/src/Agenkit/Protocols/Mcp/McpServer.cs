namespace Agenkit.Protocols.Mcp;

using System.Text.Json;
using Agenkit.Core;

/// <summary>
/// An MCP server that exposes <see cref="ITool"/> instances over the JSON-RPC protocol.
/// </summary>
public sealed class McpServer
{
    private readonly string _name;
    private readonly string _version;
    private readonly Dictionary<string, ITool> _tools;

    /// <summary>
    /// Creates a new <see cref="McpServer"/> with the given name, version, and tools.
    /// </summary>
    public McpServer(string name, string version, IEnumerable<ITool> tools)
    {
        _name = name;
        _version = version;
        _tools = tools.ToDictionary(t => t.Name);
    }

    /// <summary>Serves requests from stdin, writing responses to stdout, until EOF or cancellation.</summary>
    public async Task ServeStdioAsync(CancellationToken ct = default)
    {
        using var reader = new StreamReader(Console.OpenStandardInput());
        await using var writer = new StreamWriter(Console.OpenStandardOutput(), leaveOpen: true) { AutoFlush = true };
        while (!ct.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(ct).ConfigureAwait(false);
            if (line == null)
            {
                break;
            }

            var resp = await HandleRequestAsync(line, ct).ConfigureAwait(false);
            await writer.WriteLineAsync(JsonSerializer.Serialize(resp).AsMemory(), ct).ConfigureAwait(false);
        }
    }

    /// <summary>
    /// Handles a single JSON-RPC request string and returns a <see cref="JsonRpcResponse"/>.
    /// Public for unit testing.
    /// </summary>
    public async Task<JsonRpcResponse> HandleRequestAsync(string json, CancellationToken ct = default)
    {
        JsonRpcRequest? req;
        try
        {
            req = JsonSerializer.Deserialize<JsonRpcRequest>(json);
        }
        catch
        {
            return new JsonRpcResponse("2.0", 0, null, new McpRpcError(-32700, "parse error"));
        }

        if (req == null)
        {
            return new JsonRpcResponse("2.0", 0, null, new McpRpcError(-32700, "parse error"));
        }

        return req.Method switch
        {
            "initialize" => HandleInitialize(req),
            "tools/list" => HandleToolsList(req),
            "tools/call" => await HandleToolsCallAsync(req, ct).ConfigureAwait(false),
            _ => new JsonRpcResponse("2.0", req.Id, null, new McpRpcError(-32601, $"method not found: {req.Method}")),
        };
    }

    private JsonRpcResponse HandleInitialize(JsonRpcRequest req)
    {
        // Read (and thus stop discarding) the client's requested version —
        // agenkit#781. Per the MCP spec's negotiation model the server
        // always replies with the revision it actually implements; a
        // mismatch is logged so version skew is visible instead of silent.
        McpVersionNegotiation.WarnIfClientVersionMismatch(req.Params);

        var result = JsonSerializer.SerializeToElement(new
        {
            protocolVersion = McpConstants.ProtocolVersion,
            capabilities = new { tools = new { } },
            serverInfo = new { name = _name, version = _version },
        });
        return new JsonRpcResponse("2.0", req.Id, result, null);
    }

    private JsonRpcResponse HandleToolsList(JsonRpcRequest req)
    {
        var toolList = _tools.Values
            .Select(t => new McpTool(t.Name, t.Description))
            .ToArray();
        var result = JsonSerializer.SerializeToElement(new { tools = toolList });
        return new JsonRpcResponse("2.0", req.Id, result, null);
    }

    private async Task<JsonRpcResponse> HandleToolsCallAsync(JsonRpcRequest req, CancellationToken ct)
    {
        if (!req.Params.HasValue)
        {
            return new JsonRpcResponse("2.0", req.Id, null, new McpRpcError(-32602, "missing params"));
        }

        var p = req.Params.Value;
        if (!p.TryGetProperty("name", out var nameProp))
        {
            return new JsonRpcResponse("2.0", req.Id, null, new McpRpcError(-32602, "missing tool name"));
        }

        var toolName = nameProp.GetString() ?? "";
        if (!_tools.TryGetValue(toolName, out var tool))
        {
            return new JsonRpcResponse("2.0", req.Id, null, new McpRpcError(-32601, $"tool not found: {toolName}"));
        }

        var args = new Dictionary<string, object>();
        if (p.TryGetProperty("arguments", out var argsProp) && argsProp.ValueKind == JsonValueKind.Object)
        {
            foreach (var prop in argsProp.EnumerateObject())
            {
                args[prop.Name] = prop.Value.ValueKind == JsonValueKind.String
                    ? prop.Value.GetString() ?? ""
                    : (object)prop.Value.GetRawText();
            }
        }

        ToolResult toolResult;
        try
        {
            toolResult = await tool.ExecuteAsync(args, ct).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            toolResult = ToolResult.Fail(ex.Message);
        }

        var text = toolResult.Data?.ToString() ?? toolResult.Error ?? "";
        var mcpResult = new McpToolResult(
            [new McpContent("text", text)],
            !toolResult.Success);

        var result = JsonSerializer.SerializeToElement(mcpResult);
        return new JsonRpcResponse("2.0", req.Id, result, null);
    }
}
