using Agenkit.Core;

namespace Agenkit.Patterns;

/// <summary>Lifecycle state of a task agent.</summary>
public enum TaskState
{
    /// <summary>Agent is ready to accept a task.</summary>
    Idle,
    /// <summary>Agent is currently processing a task.</summary>
    Running,
    /// <summary>Agent completed the task successfully.</summary>
    Completed,
    /// <summary>Agent failed to complete the task.</summary>
    Failed
}

/// <summary>Configuration for TaskAgent.</summary>
public record TaskAgentConfig(IAgent Inner, TimeSpan? Timeout = null);

/// <summary>
/// One-shot task agent with explicit lifecycle management.
/// </summary>
public class TaskAgent : IAgent
{
    private readonly IAgent _inner;
    private readonly TimeSpan? _timeout;
    private TaskState _state = TaskState.Idle;
    private Message? _result;

    /// <inheritdoc />
    public string Name => "TaskAgent";

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => new[] { "task", "lifecycle" };

    /// <summary>Current lifecycle state of this task agent.</summary>
    public TaskState State => _state;

    /// <summary>Creates a new TaskAgent.</summary>
    public TaskAgent(TaskAgentConfig config)
    {
        ArgumentNullException.ThrowIfNull(config);
        _inner = config.Inner;
        _timeout = config.Timeout;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        if (_state == TaskState.Running)
            throw new InvalidOperationException("task agent is already running");

        _state = TaskState.Running;
        try
        {
            CancellationToken effectiveCt = ct;
            CancellationTokenSource? cts = null;

            if (_timeout.HasValue)
            {
                cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
                cts.CancelAfter(_timeout.Value);
                effectiveCt = cts.Token;
            }

            try
            {
                _result = await _inner.ProcessAsync(message, effectiveCt).ConfigureAwait(false);
                _state = TaskState.Completed;
                return _result;
            }
            finally
            {
                cts?.Dispose();
            }
        }
        catch (Exception)
        {
            _state = TaskState.Failed;
            throw;
        }
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        Capabilities,
        State: new Dictionary<string, object>
        {
            ["state"] = _state.ToString(),
            ["has_result"] = _result is not null
        });

    /// <summary>Resets the agent to idle state, allowing reuse.</summary>
    public void Reset()
    {
        _state = TaskState.Idle;
        _result = null;
    }
}
