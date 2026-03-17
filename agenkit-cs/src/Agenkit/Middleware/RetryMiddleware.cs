using Agenkit.Core;

namespace Agenkit.Middleware;

/// <summary>Configuration for RetryMiddleware.</summary>
public record RetryConfig(
    int MaxAttempts = 3,
    TimeSpan? InitialDelay = null,
    double BackoffMultiplier = 2.0,
    Func<Exception, bool>? ShouldRetry = null);

/// <summary>
/// Wraps an agent with exponential-backoff retry logic.
/// </summary>
public class RetryMiddleware : IAgent
{
    private readonly IAgent _inner;
    private readonly RetryConfig _config;

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => _inner.Capabilities;

    /// <summary>Creates a new RetryMiddleware.</summary>
    public RetryMiddleware(IAgent inner, RetryConfig? config = null)
    {
        _inner = inner;
        _config = config ?? new RetryConfig();
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var delay = _config.InitialDelay ?? TimeSpan.FromMilliseconds(100);
        Exception? lastEx = null;

        for (int attempt = 0; attempt < _config.MaxAttempts; attempt++)
        {
            try
            {
                return await _inner.ProcessAsync(message, ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (Exception ex)
            {
                lastEx = ex;
                var shouldRetry = _config.ShouldRetry?.Invoke(ex) ?? true;
                if (!shouldRetry || attempt >= _config.MaxAttempts - 1) throw;

                await Task.Delay(delay, ct).ConfigureAwait(false);
                delay = TimeSpan.FromTicks((long)(delay.Ticks * _config.BackoffMultiplier));
            }
        }

        throw lastEx!;
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => _inner.Introspect();
}
