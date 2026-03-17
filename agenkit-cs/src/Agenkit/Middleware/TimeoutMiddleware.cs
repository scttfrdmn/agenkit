using Agenkit.Core;

namespace Agenkit.Middleware;

/// <summary>
/// Wraps an agent with a per-request deadline.
/// </summary>
public class TimeoutMiddleware : IAgent
{
    private readonly IAgent _inner;
    private readonly TimeSpan _timeout;

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => _inner.Capabilities;

    /// <summary>Creates a new TimeoutMiddleware.</summary>
    public TimeoutMiddleware(IAgent inner, TimeSpan timeout)
    {
        if (timeout <= TimeSpan.Zero)
            throw new ArgumentOutOfRangeException(nameof(timeout), "timeout must be positive");
        _inner = inner;
        _timeout = timeout;
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(_timeout);

        try
        {
            return await _inner.ProcessAsync(message, cts.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            throw new TimeoutException(
                $"agent '{_inner.Name}' timed out after {_timeout.TotalSeconds:F1}s");
        }
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => _inner.Introspect();
}
