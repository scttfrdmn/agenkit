using Agenkit.Core;

namespace Agenkit.Evaluation;

/// <summary>
/// Runs evaluation functions against an agent.
/// </summary>
public class Evaluator
{
    private readonly IAgent _agent;
    private readonly List<(string name, Message input, Func<Message, Metric> fn)> _evals = new();

    /// <summary>Creates a new Evaluator for the given agent.</summary>
    public Evaluator(IAgent agent) => _agent = agent;

    /// <summary>Registers an evaluation case.</summary>
    /// <param name="name">Name of the evaluation.</param>
    /// <param name="input">Input message to send.</param>
    /// <param name="evaluateFn">Function that computes a Metric from the agent response.</param>
    public Evaluator AddCase(string name, Message input, Func<Message, Metric> evaluateFn)
    {
        _evals.Add((name, input, evaluateFn));
        return this;
    }

    /// <summary>Runs all evaluation cases and returns results.</summary>
    public async Task<IReadOnlyList<Metric>> RunAsync(CancellationToken ct = default)
    {
        var results = new List<Metric>();
        foreach (var (name, input, fn) in _evals)
        {
            ct.ThrowIfCancellationRequested();
            var response = await _agent.ProcessAsync(input, ct).ConfigureAwait(false);
            var metric = fn(response);
            results.Add(metric);
        }
        return results;
    }
}
