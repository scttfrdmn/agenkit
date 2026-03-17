using Agenkit.Adapters;
using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Configuration for ReflectionAgent.</summary>
public record ReflectionAgentConfig(
    ILlmClient LlmClient,
    int MaxReflections = 2,
    string? SystemPrompt = null,
    string? CritiquePrompt = null);

/// <summary>
/// An agent that generates a response, critiques it, and refines iteratively.
/// </summary>
public class ReflectionAgent : IAgent
{
    private readonly ILlmClient _llm;
    private readonly int _maxReflections;
    private readonly string _systemPrompt;
    private readonly string _critiquePrompt;
    private int _reflectionCount;

    /// <inheritdoc />
    public string Name => "ReflectionAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "reflection", "self-critique", "refinement" };

    /// <summary>Creates a new ReflectionAgent.</summary>
    public ReflectionAgent(ReflectionAgentConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        _llm = config.LlmClient;
        _maxReflections = config.MaxReflections >= 0 ? config.MaxReflections : 2;
        _systemPrompt = config.SystemPrompt ??
            "You are a helpful assistant. Provide thorough, accurate responses.";
        _critiquePrompt = config.CritiquePrompt ??
            "Review the response above. Identify any errors, gaps, or improvements needed. Be specific and constructive.";
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        _reflectionCount = 0;
        var history = new List<Message>
        {
            Message.NewMessage("system", _systemPrompt),
            message
        };

        // Generate initial response
        var response = await _llm.ChatAsync(history, ct).ConfigureAwait(false);
        history.Add(response);

        // Iterative reflection
        for (int i = 0; i < _maxReflections; i++)
        {
            ct.ThrowIfCancellationRequested();

            // Ask for critique
            history.Add(Message.NewMessage("user", _critiquePrompt));
            var critique = await _llm.ChatAsync(history, ct).ConfigureAwait(false);
            history.Add(critique);

            // Ask for refined response
            history.Add(Message.NewMessage("user",
                "Based on the critique above, provide an improved response to the original question."));
            response = await _llm.ChatAsync(history, ct).ConfigureAwait(false);
            history.Add(response);
            _reflectionCount++;
        }

        return response.WithMetadata("reflection_count", _reflectionCount);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object> { ["last_reflection_count"] = _reflectionCount });
}
