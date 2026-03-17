using System.Text;
using Agenkit.Core;

namespace Agenkit.Composition;

/// <summary>
/// Runs multiple agents concurrently and aggregates their responses.
/// </summary>
public class ParallelAgent : IAgent
{
    private readonly IReadOnlyList<IAgent> _agents;
    private readonly Func<IReadOnlyList<Message>, Message>? _aggregator;

    /// <inheritdoc />
    public string Name => "ParallelAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "parallel", "fan-out" };

    /// <summary>
    /// Creates a new ParallelAgent.
    /// </summary>
    /// <param name="agents">Agents to run concurrently.</param>
    /// <param name="aggregator">Optional custom aggregation function. Defaults to concatenation.</param>
    public ParallelAgent(IReadOnlyList<IAgent> agents, Func<IReadOnlyList<Message>, Message>? aggregator = null)
    {
        if (agents.Count == 0)
            throw new ArgumentException("at least one agent is required", nameof(agents));
        _agents = agents;
        _aggregator = aggregator;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var tasks = _agents.Select(a => a.ProcessAsync(message, ct)).ToList();
        var results = await Task.WhenAll(tasks).ConfigureAwait(false);

        return _aggregator is not null
            ? _aggregator(results)
            : DefaultAggregate(results);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object> { ["agent_count"] = _agents.Count });

    private static Message DefaultAggregate(IReadOnlyList<Message> results)
    {
        var sb = new StringBuilder();
        for (int i = 0; i < results.Count; i++)
        {
            if (i > 0) sb.AppendLine();
            sb.Append(results[i].ContentString());
        }
        return Message.NewMessage("assistant", sb.ToString());
    }
}
