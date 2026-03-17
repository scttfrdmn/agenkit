using Agenkit.Core;

namespace Agenkit.Checkpointing;

/// <summary>
/// An agent that checkpoints its state after each message.
/// </summary>
public class DurableAgent : IAgent
{
    private readonly IAgent _inner;
    private readonly CheckpointManager _manager;
    private readonly string _checkpointName;
    private int _messageCount;

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities =>
        _inner.Capabilities.Concat(new[] { "durable", "checkpointing" }).ToList();

    /// <summary>Total messages processed since last reset.</summary>
    public int MessageCount => _messageCount;

    /// <summary>Creates a new DurableAgent.</summary>
    public DurableAgent(IAgent inner, CheckpointManager manager, string? checkpointName = null)
    {
        _inner = inner;
        _manager = manager;
        _checkpointName = checkpointName ?? inner.Name;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var response = await _inner.ProcessAsync(message, ct).ConfigureAwait(false);
        _messageCount++;

        var state = new
        {
            agent = _inner.Name,
            message_count = _messageCount,
            last_message = message.ContentString(),
            last_response = response.ContentString(),
            timestamp = DateTimeOffset.UtcNow
        };

        await _manager.SaveAsync(_checkpointName, state, ct).ConfigureAwait(false);
        return response;
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["message_count"] = _messageCount,
            ["checkpoint_name"] = _checkpointName
        });
}
