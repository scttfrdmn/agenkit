namespace Agenkit.Protocols.Mcp;

using System.Text.Json;
using System.Text.Json.Serialization;

internal static class McpConstants
{
    internal const string ProtocolVersion = "2024-11-05";
    internal const string ClientVersion = "0.87.0";
}

// Wire types
public sealed record JsonRpcRequest(
    [property: JsonPropertyName("jsonrpc")] string Jsonrpc,
    [property: JsonPropertyName("id")] long Id,
    [property: JsonPropertyName("method")] string Method,
    [property: JsonPropertyName("params")] JsonElement? Params
);

public sealed record JsonRpcResponse(
    [property: JsonPropertyName("jsonrpc")] string Jsonrpc,
    [property: JsonPropertyName("id")] long Id,
    [property: JsonPropertyName("result")] JsonElement? Result,
    [property: JsonPropertyName("error")] McpRpcError? Error
);

public sealed record McpRpcError(
    [property: JsonPropertyName("code")] int Code,
    [property: JsonPropertyName("message")] string Message
);

// Public domain types
public sealed record McpTool(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("description")] string Description
);

public sealed record McpContent(
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("text")] string Text
);

public sealed record McpToolResult(
    [property: JsonPropertyName("content")] IReadOnlyList<McpContent> Content,
    [property: JsonPropertyName("isError")] bool IsError
);

public sealed record McpServerInfo(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("version")] string Version
)
{
    public static McpServerInfo Empty => new("", "");
}

// Helper
public static class McpContentExtensions
{
    public static string TextContent(this IEnumerable<McpContent> contents) =>
        string.Join(" ", contents
            .Where(c => c.Type == "text" && !string.IsNullOrEmpty(c.Text))
            .Select(c => c.Text));
}
