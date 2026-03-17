using Agenkit.Core;

namespace Agenkit.Memory;

/// <summary>
/// In-memory message store with a configurable capacity cap (LRU-style eviction).
/// </summary>
public class EphemeralMemory : IMemory
{
    private readonly int _maxMessages;
    private readonly List<Message> _messages = new();
    private readonly SemaphoreSlim _lock = new(1, 1);

    /// <summary>Creates an EphemeralMemory with the given capacity.</summary>
    public EphemeralMemory(int maxMessages = 100)
    {
        _maxMessages = maxMessages > 0 ? maxMessages : 100;
    }

    /// <inheritdoc />
    public async Task StoreAsync(Message message, CancellationToken ct = default)
    {
        await _lock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            _messages.Add(message);
            if (_messages.Count > _maxMessages)
                _messages.RemoveAt(0);
        }
        finally
        {
            _lock.Release();
        }
    }

    /// <inheritdoc />
    public async Task<IReadOnlyList<Message>> RetrieveAsync(int count = 10, CancellationToken ct = default)
    {
        await _lock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            var skip = Math.Max(0, _messages.Count - count);
            return _messages.Skip(skip).ToList();
        }
        finally
        {
            _lock.Release();
        }
    }

    /// <inheritdoc />
    public async Task ClearAsync(CancellationToken ct = default)
    {
        await _lock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            _messages.Clear();
        }
        finally
        {
            _lock.Release();
        }
    }

    /// <summary>Total number of stored messages.</summary>
    public int Count
    {
        get
        {
            _lock.Wait();
            try { return _messages.Count; }
            finally { _lock.Release(); }
        }
    }
}
