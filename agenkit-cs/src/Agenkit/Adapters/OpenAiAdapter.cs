using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Agenkit.Core;

namespace Agenkit.Adapters;

/// <summary>
/// HTTP REST client for the OpenAI Chat Completions API.
/// Uses HttpClient directly — no SDK dependency.
/// </summary>
public class OpenAiAdapter : ILlmClient, IDisposable
{
    private readonly HttpClient _http;
    private readonly string _model;
    private bool _disposed;

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    /// <summary>Creates an OpenAI adapter.</summary>
    /// <param name="apiKey">OpenAI API key.</param>
    /// <param name="model">Model name, e.g. "gpt-4o".</param>
    /// <param name="httpClient">Optional custom HttpClient.</param>
    public OpenAiAdapter(string apiKey, string model = "gpt-4o", HttpClient? httpClient = null)
    {
        if (string.IsNullOrWhiteSpace(apiKey))
            throw new ArgumentException("api key cannot be empty", nameof(apiKey));

        _model = model;
        _http = httpClient ?? new HttpClient();
        _http.BaseAddress ??= new Uri("https://api.openai.com/");
        _http.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", apiKey);
    }

    /// <inheritdoc />
    public async Task<Message> ChatAsync(IList<Message> messages, CancellationToken ct = default)
    {
        var payload = new
        {
            model = _model,
            messages = messages.Select(m => new { role = m.Role, content = m.ContentString() }).ToList()
        };

        var json = JsonSerializer.Serialize(payload, JsonOpts);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");
        using var response = await _http.PostAsync("v1/chat/completions", content, ct).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();

        var body = await response.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
        using var doc = JsonDocument.Parse(body);
        var text = doc.RootElement
            .GetProperty("choices")[0]
            .GetProperty("message")
            .GetProperty("content")
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
