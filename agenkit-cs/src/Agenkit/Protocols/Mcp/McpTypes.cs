namespace Agenkit.Protocols.Mcp;

using System.Text.Json;
using System.Text.Json.Serialization;

/// <summary>
/// Shared protocol constants used across MCP client and server implementations.
/// </summary>
public static class McpConstants
{
    /// <summary>
    /// The MCP protocol revision this implementation speaks. A single named
    /// constant (agenkit#781) referenced by both client and server code,
    /// rather than each repeating the literal, so a version bump is a
    /// one-line change and the two halves of the protocol cannot drift from
    /// each other.
    ///
    /// <para>
    /// <c>2025-11-25</c> is the latest <i>ratified</i> revision whose
    /// initialize/tools/list/tools/call surface is additive over
    /// <c>2024-11-05</c> (agenkit#733: the <c>2026-07-28</c> revision
    /// removes the initialize handshake in favor of a stateless core this
    /// package does not implement, so advertising that literal would claim
    /// a handshake the wire no longer has).
    /// </para>
    /// </summary>
    public const string ProtocolVersion = "2025-11-25";
    internal const string ClientVersion = "0.92.0";
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

/// <param name="Name">Server name as self-reported during initialization.</param>
/// <param name="Version">Server version string.</param>
/// <param name="ProtocolVersion">
/// The MCP protocol revision the server actually reported in its
/// initialize response (the top-level <c>result.protocolVersion</c>
/// field). Captured so a caller has a single place to check it after
/// <c>InitializeAsync</c> (agenkit#781 — this field did not exist before,
/// so a peer speaking a different revision was indistinguishable from one
/// speaking ours).
/// </param>
public sealed record McpServerInfo(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("protocolVersion")] string ProtocolVersion = ""
)
{
    public static McpServerInfo Empty => new("", "", "");
}

// Helper
public static class McpContentExtensions
{
    public static string TextContent(this IEnumerable<McpContent> contents) =>
        string.Join(" ", contents
            .Where(c => c.Type == "text" && !string.IsNullOrEmpty(c.Text))
            .Select(c => c.Text));
}

/// <summary>
/// Protocol version negotiation helpers shared by client and server (agenkit#781).
/// </summary>
internal static class McpVersionNegotiation
{
    /// <summary>
    /// Builds an <see cref="McpServerInfo"/> from a raw initialize result,
    /// capturing the server's reported <c>protocolVersion</c> (previously
    /// discarded) and warning to stderr when it differs from ours, so
    /// version skew is visible instead of surfacing later as an unrelated
    /// decode error or wrong result.
    /// </summary>
    public static McpServerInfo ParseServerInfo(JsonElement result)
    {
        string name = "", version = "", protocolVersion = "";
        if (result.TryGetProperty("serverInfo", out var info))
        {
            name = info.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
            version = info.TryGetProperty("version", out var v) ? v.GetString() ?? "" : "";
        }
        if (result.TryGetProperty("protocolVersion", out var pv))
        {
            protocolVersion = pv.GetString() ?? "";
        }

        if (protocolVersion != "" && protocolVersion != McpConstants.ProtocolVersion)
        {
            Console.Error.WriteLine(
                $"mcp: server protocol version \"{protocolVersion}\" does not match client version \"{McpConstants.ProtocolVersion}\"");
        }

        return new McpServerInfo(name, version, protocolVersion);
    }

    /// <summary>
    /// Reads (and thus stops discarding) the client's requested
    /// <c>protocolVersion</c> from an initialize request's params, warning
    /// to stderr on a mismatch. Per the MCP spec's negotiation model the
    /// server always replies with the revision it actually implements.
    /// </summary>
    public static void WarnIfClientVersionMismatch(JsonElement? @params)
    {
        if (@params is not JsonElement p || !p.TryGetProperty("protocolVersion", out var pv))
        {
            return;
        }

        var clientProtocolVersion = pv.GetString() ?? "";
        if (clientProtocolVersion != "" && clientProtocolVersion != McpConstants.ProtocolVersion)
        {
            Console.Error.WriteLine(
                $"mcp: client requested protocol version \"{clientProtocolVersion}\", server speaks \"{McpConstants.ProtocolVersion}\"");
        }
    }
}
