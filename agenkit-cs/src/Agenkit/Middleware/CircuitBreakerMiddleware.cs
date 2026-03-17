using Agenkit.Core;

namespace Agenkit.Middleware;

/// <summary>Circuit breaker state.</summary>
public enum CircuitState
{
    /// <summary>Normal operation — requests pass through.</summary>
    Closed,
    /// <summary>Circuit is open — requests fail fast.</summary>
    Open,
    /// <summary>One test request is allowed to probe recovery.</summary>
    HalfOpen
}

/// <summary>Configuration for CircuitBreakerMiddleware.</summary>
public record CircuitBreakerConfig(
    int FailureThreshold = 5,
    TimeSpan? ResetTimeout = null,
    int SuccessThreshold = 1);

/// <summary>
/// Wraps an agent with a circuit breaker to prevent cascading failures.
/// </summary>
public class CircuitBreakerMiddleware : IAgent
{
    private readonly IAgent _inner;
    private readonly CircuitBreakerConfig _config;
    private CircuitState _state = CircuitState.Closed;
    private int _failureCount;
    private int _successCount;
    private DateTimeOffset _openedAt;
    private readonly object _stateLock = new();

    /// <summary>Current state of the circuit breaker.</summary>
    public CircuitState State => _state;

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => _inner.Capabilities;

    /// <summary>Creates a new CircuitBreakerMiddleware.</summary>
    public CircuitBreakerMiddleware(IAgent inner, CircuitBreakerConfig? config = null)
    {
        _inner = inner;
        _config = config ?? new CircuitBreakerConfig();
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        lock (_stateLock)
        {
            switch (_state)
            {
                case CircuitState.Open:
                    var elapsed = DateTimeOffset.UtcNow - _openedAt;
                    var resetTimeout = _config.ResetTimeout ?? TimeSpan.FromSeconds(30);
                    if (elapsed < resetTimeout)
                        throw new InvalidOperationException($"circuit breaker for '{_inner.Name}' is open");
                    _state = CircuitState.HalfOpen;
                    _successCount = 0;
                    break;
            }
        }

        try
        {
            var result = await _inner.ProcessAsync(message, ct).ConfigureAwait(false);
            OnSuccess();
            return result;
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch
        {
            OnFailure();
            throw;
        }
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        _inner.Capabilities,
        State: new Dictionary<string, object>
        {
            ["circuit_state"] = _state.ToString(),
            ["failure_count"] = _failureCount
        });

    private void OnSuccess()
    {
        lock (_stateLock)
        {
            _failureCount = 0;
            if (_state == CircuitState.HalfOpen)
            {
                _successCount++;
                if (_successCount >= _config.SuccessThreshold)
                    _state = CircuitState.Closed;
            }
        }
    }

    private void OnFailure()
    {
        lock (_stateLock)
        {
            _failureCount++;
            if (_state == CircuitState.HalfOpen || _failureCount >= _config.FailureThreshold)
            {
                _state = CircuitState.Open;
                _openedAt = DateTimeOffset.UtcNow;
            }
        }
    }
}
