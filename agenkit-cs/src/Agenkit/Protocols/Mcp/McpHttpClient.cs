namespace Agenkit.Protocols.Mcp;

using System.Text;
using System.Text.Json;

/// <summary>
/// MCP client that communicates with an HTTP endpoint using JSON-RPC over POST.
/// Named <c>McpHttpClient</c> to avoid collision with <see cref="System.Net.Http.HttpClient"/>.
/// </summary>
public sealed class McpHttpClient : IMcpClient
{
    private readonly string _baseUrl;
    private readonly System.Net.Http.HttpClient _http = new();
    private long _nextId;
    private McpServerInfo _serverInfo = McpServerInfo.Empty;

    /// <summary>Creates a new <see cref="McpHttpClient"/> targeting the given base URL.</summary>
    public McpHttpClient(string baseUrl) => _baseUrl = baseUrl.TrimEnd('/');

    /// <inheritdoc />
    public McpServerInfo ServerInfo => _serverInfo;

    private async Task<JsonRpcResponse> SendRequestAsync(string method, JsonElement? @params, CancellationToken ct)
    {
        var id = Interlocked.Increment(ref _nextId);
        var req = new JsonRpcRequest("2.0", id, method, @params);
        var content = new StringContent(JsonSerializer.Serialize(req), Encoding.UTF8, "application/json");
        var httpResp = await _http.PostAsync(_baseUrl, content, ct).ConfigureAwait(false);
        httpResp.EnsureSuccessStatusCode();
        var body = await httpResp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
        return JsonSerializer.Deserialize<JsonRpcResponse>(body)
            ?? throw new InvalidOperationException("mcp: null response");
    }

    /// <inheritdoc />
    public async Task InitializeAsync(CancellationToken ct = default)
    {
        var initParams = JsonSerializer.SerializeToElement(new
        {
            protocolVersion = McpConstants.ProtocolVersion,
            capabilities = new { },
            clientInfo = new { name = "agenkit", version = McpConstants.ClientVersion },
        });

        var resp = await SendRequestAsync("initialize", initParams, ct).ConfigureAwait(false);
        if (resp.Error != null)
        {
            throw new InvalidOperationException($"mcp initialize error {resp.Error.Code}: {resp.Error.Message}");
        }

        if (resp.Result.HasValue)
        {
            _serverInfo = McpVersionNegotiation.ParseServerInfo(resp.Result.Value);
        }
    }

    /// <inheritdoc />
    public async Task<IReadOnlyList<McpTool>> ListToolsAsync(CancellationToken ct = default)
    {
        var resp = await SendRequestAsync("tools/list", null, ct).ConfigureAwait(false);
        if (resp.Error != null)
        {
            throw new InvalidOperationException(resp.Error.Message);
        }

        if (!resp.Result.HasValue)
        {
            return Array.Empty<McpTool>();
        }

        return resp.Result.Value.TryGetProperty("tools", out var t)
            ? JsonSerializer.Deserialize<McpTool[]>(t)?.ToList() ?? []
            : [];
    }

    /// <inheritdoc />
    public async Task<McpToolResult> CallToolAsync(string name, IDictionary<string, object> args, CancellationToken ct = default)
    {
        var p = JsonSerializer.SerializeToElement(new { name, arguments = args });
        var resp = await SendRequestAsync("tools/call", p, ct).ConfigureAwait(false);
        if (resp.Error != null)
        {
            throw new InvalidOperationException(resp.Error.Message);
        }

        if (!resp.Result.HasValue)
        {
            return new McpToolResult([], false);
        }

        return JsonSerializer.Deserialize<McpToolResult>(resp.Result.Value) ?? new McpToolResult([], false);
    }

    /// <inheritdoc />
    public void Dispose() => _http.Dispose();
}
