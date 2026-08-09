namespace Agenkit.Protocols.Mcp;

using System.Diagnostics;
using System.Text.Json;

/// <summary>
/// MCP client that communicates with a subprocess over stdin/stdout.
/// </summary>
public sealed class StdioClient : IMcpClient
{
    private readonly string _command;
    private readonly string[] _args;
    private Process? _process;
    private StreamWriter? _writer;
    private StreamReader? _reader;
    private long _nextId;
    private readonly SemaphoreSlim _lock = new(1, 1);
    private McpServerInfo _serverInfo = McpServerInfo.Empty;

    /// <summary>Creates a new <see cref="StdioClient"/> that will launch the given command.</summary>
    public StdioClient(string command, params string[] args)
    {
        _command = command;
        _args = args;
    }

    /// <inheritdoc />
    public McpServerInfo ServerInfo => _serverInfo;

    /// <inheritdoc />
    public async Task InitializeAsync(CancellationToken ct = default)
    {
        var psi = new ProcessStartInfo(_command)
        {
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = false,
        };
        foreach (var a in _args)
        {
            psi.ArgumentList.Add(a);
        }

        _process = Process.Start(psi) ?? throw new InvalidOperationException("mcp: failed to start process");
        _writer = _process.StandardInput;
        _reader = _process.StandardOutput;

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

    private async Task<JsonRpcResponse> SendRequestAsync(string method, JsonElement? @params, CancellationToken ct)
    {
        await _lock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            var id = Interlocked.Increment(ref _nextId);
            var req = new JsonRpcRequest("2.0", id, method, @params);
            var json = JsonSerializer.Serialize(req);
            await _writer!.WriteLineAsync(json.AsMemory(), ct).ConfigureAwait(false);
            await _writer.FlushAsync(ct).ConfigureAwait(false);
            var line = await _reader!.ReadLineAsync(ct).ConfigureAwait(false);
            if (line == null)
            {
                throw new InvalidOperationException("mcp: server closed stdout");
            }

            return JsonSerializer.Deserialize<JsonRpcResponse>(line)
                ?? throw new InvalidOperationException("mcp: null response");
        }
        finally
        {
            _lock.Release();
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
    public void Dispose()
    {
        _writer?.Close();
        _process?.WaitForExit(5000);
        _process?.Dispose();
        _lock.Dispose();
    }
}
