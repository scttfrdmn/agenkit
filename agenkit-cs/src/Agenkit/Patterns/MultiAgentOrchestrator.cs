using System.Text;
using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Configuration for MultiAgentOrchestrator.</summary>
public record MultiAgentOrchestratorConfig(
    IReadOnlyDictionary<string, IAgent> Agents,
    IReadOnlyList<string>? ExecutionOrder = null);

/// <summary>
/// Coordinates named agents in a defined execution order.
/// </summary>
public class MultiAgentOrchestrator : IAgent
{
    private readonly IReadOnlyDictionary<string, IAgent> _agents;
    private readonly IReadOnlyList<string> _order;

    /// <inheritdoc />
    public string Name => "MultiAgentOrchestrator";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "multi-agent", "coordination", "orchestration" };

    /// <summary>Creates a new MultiAgentOrchestrator.</summary>
    public MultiAgentOrchestrator(MultiAgentOrchestratorConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        if (config.Agents.Count == 0)
            throw new ArgumentException("at least one agent is required", nameof(config));

        _agents = config.Agents;
        _order = config.ExecutionOrder ?? config.Agents.Keys.ToList();

        // Validate order
        foreach (var key in _order)
        {
            if (!_agents.ContainsKey(key))
                throw new ArgumentException($"execution order references unknown agent '{key}'", nameof(config));
        }
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var results = new Dictionary<string, Message>();
        var current = message;

        foreach (var key in _order)
        {
            ct.ThrowIfCancellationRequested();
            var agent = _agents[key];
            var result = await agent.ProcessAsync(current, ct).ConfigureAwait(false);
            results[key] = result;
            current = result; // pass output to next agent
        }

        // Final response includes all agent outputs
        var final = results[_order[^1]];
        return final.WithMetadata("agent_count", _agents.Count)
                    .WithMetadata("execution_order", _order.ToList());
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["agent_count"] = _agents.Count,
            ["execution_order"] = _order.ToList()
        });
}
