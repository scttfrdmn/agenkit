using Agenkit.Core;

namespace Agenkit.Middleware;

/// <summary>Configuration for BatchingMiddleware.</summary>
public record BatchingConfig(
    int MaxBatchSize = 10,
    TimeSpan? Window = null);

/// <summary>
/// Coalesces multiple concurrent requests within a time window into a single call.
/// </summary>
public class BatchingMiddleware : IAgent
{
    private readonly IAgent _inner;
    private readonly int _maxBatchSize;
    private readonly TimeSpan _window;
    private readonly List<(Message message, TaskCompletionSource<Message> tcs)> _pending = new();
    private readonly SemaphoreSlim _lock = new(1, 1);
    private Task? _flushTask;

    /// <inheritdoc />
    public string Name => _inner.Name;

    /// <inheritdoc />
    public IReadOnlyList<string> Capabilities => _inner.Capabilities;

    /// <summary>Creates a new BatchingMiddleware.</summary>
    public BatchingMiddleware(IAgent inner, BatchingConfig? config = null)
    {
        _inner = inner;
        config ??= new BatchingConfig();
        _maxBatchSize = config.MaxBatchSize > 0 ? config.MaxBatchSize : 10;
        _window = config.Window ?? TimeSpan.FromMilliseconds(10);
    }

    /// <inheritdoc />
    public async Task<Message> ProcessAsync(Message message, CancellationToken ct = default)
    {
        var tcs = new TaskCompletionSource<Message>(TaskCreationOptions.RunContinuationsAsynchronously);

        await _lock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            _pending.Add((message, tcs));
            if (_pending.Count >= _maxBatchSize)
            {
                _ = FlushBatchAsync();
            }
            else if (_flushTask is null || _flushTask.IsCompleted)
            {
                _flushTask = ScheduleFlushAsync();
            }
        }
        finally
        {
            _lock.Release();
        }

        ct.Register(() => tcs.TrySetCanceled(ct));
        return await tcs.Task.ConfigureAwait(false);
    }

    /// <inheritdoc />
    public IntrospectionResult Introspect() => new(
        Name,
        _inner.Capabilities,
        State: new Dictionary<string, object> { ["pending_count"] = _pending.Count });

    private async Task ScheduleFlushAsync()
    {
        await Task.Delay(_window).ConfigureAwait(false);
        await FlushBatchAsync().ConfigureAwait(false);
    }

    private async Task FlushBatchAsync()
    {
        List<(Message message, TaskCompletionSource<Message> tcs)> batch;

        await _lock.WaitAsync().ConfigureAwait(false);
        try
        {
            batch = _pending.ToList();
            _pending.Clear();
        }
        finally
        {
            _lock.Release();
        }

        if (batch.Count == 0) return;

        foreach (var (msg, tcs) in batch)
        {
            try
            {
                var result = await _inner.ProcessAsync(msg).ConfigureAwait(false);
                tcs.TrySetResult(result);
            }
            catch (Exception ex)
            {
                tcs.TrySetException(ex);
            }
        }
    }
}
