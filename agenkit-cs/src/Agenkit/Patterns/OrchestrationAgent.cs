using System.Text;
using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Orchestration execution mode.</summary>
public enum OrchestrationMode
{
    /// <summary>Execute agents sequentially, passing output to next.</summary>
    Sequential,
    /// <summary>Execute agents in parallel, combine results.</summary>
    Parallel,
    /// <summary>Route to agent based on classifier.</summary>
    Router
}

/// <summary>Configuration for OrchestrationAgent.</summary>
public record OrchestrationAgentConfig(
    IReadOnlyList<IAgent> Agents,
    OrchestrationMode Mode = OrchestrationMode.Sequential,
    Func<Message, int>? RouterFn = null);

/// <summary>
/// Unified orchestrator that supports sequential, parallel, and router modes.
/// </summary>
public class OrchestrationAgent : IAgent
{
    private readonly IReadOnlyList<IAgent> _agents;
    private readonly OrchestrationMode _mode;
    private readonly Func<Message, int>? _routerFn;

    /// <inheritdoc />
    public string Name => "OrchestrationAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "orchestration", _mode.ToString().ToLowerInvariant() };

    /// <summary>Creates a new OrchestrationAgent.</summary>
    public OrchestrationAgent(OrchestrationAgentConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        if (config.Agents.Count == 0)
            throw new ArgumentException("at least one agent is required", nameof(config));
        if (config.Mode == OrchestrationMode.Router && config.RouterFn is null)
            throw new ArgumentException("router mode requires a RouterFn", nameof(config));
        _agents = config.Agents;
        _mode = config.Mode;
        _routerFn = config.RouterFn;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        return _mode switch
        {
            OrchestrationMode.Sequential => await RunSequentialAsync(message, ct).ConfigureAwait(false),
            OrchestrationMode.Parallel => await RunParallelAsync(message, ct).ConfigureAwait(false),
            OrchestrationMode.Router => await RunRouterAsync(message, ct).ConfigureAwait(false),
            _ => throw new InvalidOperationException($"unknown orchestration mode: {_mode}")
        };
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["mode"] = _mode.ToString(),
            ["agent_count"] = _agents.Count
        });

    private async Task<Message> RunSequentialAsync(Message message, CancellationToken ct)
    {
        var current = message;
        foreach (var agent in _agents)
        {
            ct.ThrowIfCancellationRequested();
            current = await agent.ProcessAsync(current, ct).ConfigureAwait(false);
        }
        return current;
    }

    private async Task<Message> RunParallelAsync(Message message, CancellationToken ct)
    {
        var tasks = _agents.Select(a => a.ProcessAsync(message, ct)).ToList();
        var results = await Task.WhenAll(tasks).ConfigureAwait(false);

        var sb = new StringBuilder();
        for (int i = 0; i < results.Length; i++)
        {
            if (i > 0) sb.AppendLine();
            sb.Append(results[i].ContentString());
        }

        return Message.NewMessage("assistant", sb.ToString());
    }

    private async Task<Message> RunRouterAsync(Message message, CancellationToken ct)
    {
        var idx = _routerFn!(message);
        if (idx < 0 || idx >= _agents.Count)
            throw new IndexOutOfRangeException(
                $"router returned index {idx} but only {_agents.Count} agents are registered");
        return await _agents[idx].ProcessAsync(message, ct).ConfigureAwait(false);
    }
}
