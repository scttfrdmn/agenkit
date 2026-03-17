using Agenkit.Core;

namespace Agenkit.Composition;

/// <summary>
/// Runs a pipeline of agents sequentially, passing each output as input to the next.
/// </summary>
public class SequentialAgent : IAgent
{
    private readonly IReadOnlyList<IAgent> _pipeline;

    /// <inheritdoc />
    public string Name => "SequentialAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "sequential", "pipeline" };

    /// <summary>Creates a new SequentialAgent.</summary>
    public SequentialAgent(IReadOnlyList<IAgent> pipeline)
    {
        if (pipeline.Count == 0)
            throw new ArgumentException("pipeline must contain at least one agent", nameof(pipeline));
        _pipeline = pipeline;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var current = message;
        foreach (var agent in _pipeline)
        {
            ct.ThrowIfCancellationRequested();
            current = await agent.ProcessAsync(current, ct).ConfigureAwait(false);
        }
        return current;
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object> { ["pipeline_length"] = _pipeline.Count });
}
