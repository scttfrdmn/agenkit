using Agenkit.Adapters;
using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>
/// Configuration for ConversationalAgent.
/// </summary>
public record ConversationalAgentConfig(
    ILlmClient LlmClient,
    int MaxHistory = 10,
    string? SystemPrompt = null);

/// <summary>
/// A multi-turn conversational agent that maintains a history window.
/// </summary>
public class ConversationalAgent : IAgent
{
    private readonly ILlmClient _llmClient;
    private readonly int _maxHistory;
    private readonly string? _systemPrompt;
    private readonly List<Message> _history = new();

    /// <inheritdoc />
    public string Name => "ConversationalAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "conversational", "history-management" };

    /// <summary>Creates a new ConversationalAgent.</summary>
    public ConversationalAgent(ConversationalAgentConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        _llmClient = config.LlmClient;
        _maxHistory = config.MaxHistory > 0 ? config.MaxHistory : 10;
        _systemPrompt = config.SystemPrompt;

        if (config.SystemPrompt is not null)
            _history.Add(Message.NewMessage("system", config.SystemPrompt));
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        _history.Add(message);
        PruneHistory();

        var response = await _llmClient.ChatAsync(_history, ct).ConfigureAwait(false);
        _history.Add(response);
        PruneHistory();

        return response;
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object> { ["history_count"] = _history.Count });

    /// <summary>Returns the full conversation history.</summary>
    public IReadOnlyList<Message> GetHistory() => _history.AsReadOnly();

    /// <summary>Clears conversation history, optionally retaining the system message.</summary>
    public void ClearHistory(bool keepSystem = true)
    {
        _history.Clear();
        if (keepSystem && _systemPrompt is not null)
            _history.Add(Message.NewMessage("system", _systemPrompt));
    }

    private void PruneHistory()
    {
        if (_history.Count <= _maxHistory) return;

        var systemMsgs = _history.Where(m => m.Role == "system").ToList();
        var convMsgs = _history.Where(m => m.Role != "system").ToList();
        var keep = Math.Max(0, _maxHistory - systemMsgs.Count);
        var kept = convMsgs.Skip(Math.Max(0, convMsgs.Count - keep)).ToList();

        _history.Clear();
        _history.AddRange(systemMsgs);
        _history.AddRange(kept);
    }
}
