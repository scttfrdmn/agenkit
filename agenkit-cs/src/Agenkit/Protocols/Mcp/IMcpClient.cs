namespace Agenkit.Protocols.Mcp;

/// <summary>
/// Client interface for interacting with an MCP (Model Context Protocol) server.
/// </summary>
public interface IMcpClient : IDisposable
{
    /// <summary>Initializes the MCP session by performing the protocol handshake.</summary>
    Task InitializeAsync(CancellationToken ct = default);

    /// <summary>Lists all tools exposed by the MCP server.</summary>
    Task<IReadOnlyList<McpTool>> ListToolsAsync(CancellationToken ct = default);

    /// <summary>Calls a named tool on the MCP server with the given arguments.</summary>
    Task<McpToolResult> CallToolAsync(string name, IDictionary<string, object> args, CancellationToken ct = default);

    /// <summary>Returns server metadata populated after <see cref="InitializeAsync"/>.</summary>
    McpServerInfo ServerInfo { get; }
}
