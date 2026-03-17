using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Agenkit.Core;

namespace Agenkit.Adapters;

/// <summary>
/// HTTP REST client for the Anthropic Messages API.
/// Uses HttpClient directly — no SDK dependency.
/// </summary>
public class AnthropicAdapter : ILlmClient, IDisposable
{
    private readonly HttpClient _http;
    private readonly string _model;
    private bool _disposed;

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    /// <summary>Creates an Anthropic adapter.</summary>
    /// <param name="apiKey">Anthropic API key.</param>
    /// <param name="model">Model name, e.g. "claude-3-5-sonnet-20241022".</param>
    /// <param name="httpClient">Optional custom HttpClient.</param>
    public AnthropicAdapter(string apiKey, string model = "claude-3-5-sonnet-20241022", HttpClient? httpClient = null)
    {
        if (string.IsNullOrWhiteSpace(apiKey))
            throw new ArgumentException("api key cannot be empty", nameof(apiKey));

        _model = model;
        _http = httpClient ?? new HttpClient();
        _http.BaseAddress ??= new Uri("https://api.anthropic.com/");
        _http.DefaultRequestHeaders.Add("x-api-key", apiKey);
        _http.DefaultRequestHeaders.Add("anthropic-version", "2023-06-01");
        _http.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
    }

    /// <inheritdoc />
    public async Task<Message> ChatAsync(IList<Message> messages, CancellationToken ct = default)
    {
        // Separate system from conversation messages
        var systemMessages = messages.Where(m => m.Role == "system").ToList();
        var conversationMessages = messages.Where(m => m.Role != "system").ToList();
        var systemText = systemMessages.Count > 0
            ? string.Join("\n", systemMessages.Select(m => m.ContentString()))
            : null;

        var payload = new Dictionary<string, object?>
        {
            ["model"] = _model,
            ["max_tokens"] = 1024,
            ["messages"] = conversationMessages
                .Select(m => new { role = m.Role == "agent" ? "assistant" : m.Role, content = m.ContentString() })
                .ToList()
        };

        if (systemText is not null)
            payload["system"] = systemText;

        var json = JsonSerializer.Serialize(payload, JsonOpts);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");
        using var response = await _http.PostAsync("v1/messages", content, ct).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();

        var body = await response.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
        using var doc = JsonDocument.Parse(body);
        var text = doc.RootElement
            .GetProperty("content")[0]
            .GetProperty("text")
            .GetString() ?? "";

        return Message.NewMessage("assistant", text);
    }

    /// <inheritdoc />
    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _http.Dispose();
    }
}
