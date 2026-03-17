using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Configuration for AutonomousAgent.</summary>
public record AutonomousAgentConfig(
    IAgent Inner,
    Func<Message, bool> GoalChecker,
    int MaxIterations = 10,
    string? InitialPrompt = null);

/// <summary>
/// Goal-driven agent that iterates until a goal condition is met or max iterations are reached.
/// </summary>
public class AutonomousAgent : IAgent
{
    private readonly IAgent _inner;
    private readonly Func<Message, bool> _goalChecker;
    private readonly int _maxIterations;
    private readonly string? _initialPrompt;
    private int _lastIterationCount;

    /// <inheritdoc />
    public string Name => "AutonomousAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "autonomous", "goal-driven", "iterative" };

    /// <summary>Creates a new AutonomousAgent.</summary>
    public AutonomousAgent(AutonomousAgentConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        _inner = config.Inner;
        _goalChecker = config.GoalChecker;
        _maxIterations = config.MaxIterations > 0 ? config.MaxIterations : 10;
        _initialPrompt = config.InitialPrompt;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        _lastIterationCount = 0;
        var current = message;

        if (_initialPrompt is not null)
            current = Message.NewMessage("user", $"{_initialPrompt}\n\n{message.ContentString()}");

        Message? lastResponse = null;

        for (int i = 0; i < _maxIterations; i++)
        {
            ct.ThrowIfCancellationRequested();
            _lastIterationCount = i + 1;

            var response = await _inner.ProcessAsync(current, ct).ConfigureAwait(false);
            lastResponse = response;

            if (_goalChecker(response))
                return response.WithMetadata("iterations", _lastIterationCount)
                               .WithMetadata("goal_reached", true);

            // Feed the response back as a new prompt for the next iteration
            current = Message.NewMessage("user",
                $"Previous response: {response.ContentString()}\n\nContinue working toward the goal.");
        }

        var final = lastResponse ?? Message.NewMessage("assistant", "Max iterations reached without achieving goal.");
        return final.WithMetadata("iterations", _lastIterationCount)
                    .WithMetadata("goal_reached", false);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["max_iterations"] = _maxIterations,
            ["last_iteration_count"] = _lastIterationCount
        });
}
