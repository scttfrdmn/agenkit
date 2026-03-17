using Agenkit.Core;
using Agenkit.Memory;

namespace Agenkit.Patterns;

/// <summary>Configuration for MemoryAugmentedAgent.</summary>
public record MemoryAugmentedAgentConfig(
    IAgent Inner,
    IMemory Memory,
    int ContextMessages = 5,
    string? SystemPrompt = null);

/// <summary>
/// Wraps an agent with persistent memory that provides context from past interactions.
/// </summary>
public class MemoryAugmentedAgent : IAgent
{
    private readonly IAgent _inner;
    private readonly IMemory _memory;
    private readonly int _contextMessages;
    private readonly string? _systemPrompt;

    /// <inheritdoc />
    public string Name => "MemoryAugmentedAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities =>
        _inner.Capabilities.Concat(new[] { "memory", "context-aware" }).ToList();

    /// <summary>Creates a new MemoryAugmentedAgent.</summary>
    public MemoryAugmentedAgent(MemoryAugmentedAgentConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        _inner = config.Inner;
        _memory = config.Memory;
        _contextMessages = config.ContextMessages > 0 ? config.ContextMessages : 5;
        _systemPrompt = config.SystemPrompt;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        // Store incoming message
        await _memory.StoreAsync(message, ct).ConfigureAwait(false);

        // Retrieve recent context
        var context = await _memory.RetrieveAsync(_contextMessages, ct).ConfigureAwait(false);

        // Build augmented message
        string augmented;
        if (context.Count > 1) // more than just the current message
        {
            var history = string.Join("\n", context.Take(context.Count - 1)
                .Select(m => $"{m.Role}: {m.ContentString()}"));
            augmented = $"Recent context:\n{history}\n\nCurrent message: {message.ContentString()}";
        }
        else
        {
            augmented = message.ContentString();
        }

        if (_systemPrompt is not null)
            augmented = $"{_systemPrompt}\n\n{augmented}";

        var response = await _inner.ProcessAsync(
            Message.NewMessage("user", augmented), ct).ConfigureAwait(false);

        // Store the response too
        await _memory.StoreAsync(response, ct).ConfigureAwait(false);

        return response;
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        Memory: new Dictionary<string, object> { ["context_messages"] = _contextMessages });
}
