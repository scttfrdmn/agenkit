namespace Agenkit.Protocols.Mcp;

using Agenkit.Core;

/// <summary>
/// Wraps an <see cref="McpTool"/> as an <see cref="ITool"/> so MCP tools can be used
/// wherever a local tool is expected.
/// </summary>
internal sealed class McpToolAdapter : ITool
{
    private readonly IMcpClient _client;
    private readonly McpTool _mcpTool;

    internal McpToolAdapter(IMcpClient client, McpTool mcpTool)
    {
        _client = client;
        _mcpTool = mcpTool;
    }

    /// <inheritdoc />
    public string Name => _mcpTool.Name;

    /// <inheritdoc />
    public string Description => _mcpTool.Description;

    /// <inheritdoc />
    public async Task<ToolResult> ExecuteAsync(IDictionary<string, object> parameters, CancellationToken ct = default)
    {
        try
        {
            var result = await _client.CallToolAsync(Name, parameters, ct).ConfigureAwait(false);
            var text = result.Content.TextContent();
            return result.IsError ? ToolResult.Fail(text) : ToolResult.Ok(text);
        }
        catch (Exception e)
        {
            return ToolResult.Fail(e.Message);
        }
    }
}

/// <summary>
/// Extension methods for <see cref="IMcpClient"/>.
/// </summary>
public static class McpExtensions
{
    /// <summary>
    /// Fetches all tools from an MCP client and wraps each as an <see cref="ITool"/>.
    /// </summary>
    public static async Task<IReadOnlyList<ITool>> ToolsFromClientAsync(
        this IMcpClient client, CancellationToken ct = default)
    {
        var tools = await client.ListToolsAsync(ct).ConfigureAwait(false);
        return tools.Select(t => (ITool)new McpToolAdapter(client, t)).ToList();
    }
}
