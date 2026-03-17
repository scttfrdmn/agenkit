using Agenkit.Core;

namespace Agenkit.Memory;

/// <summary>
/// Three-tier memory hierarchy: working / short-term / long-term.
/// </summary>
public class MemoryHierarchy : IMemory
{
    private readonly EphemeralMemory _working;
    private readonly EphemeralMemory _shortTerm;
    private readonly EphemeralMemory _longTerm;
    private readonly int _workingCapacity;
    private readonly int _shortTermCapacity;

    /// <summary>
    /// Creates a MemoryHierarchy.
    /// </summary>
    /// <param name="workingCapacity">Max messages in working memory before promotion.</param>
    /// <param name="shortTermCapacity">Max messages in short-term memory before promotion.</param>
    /// <param name="longTermCapacity">Max messages in long-term memory.</param>
    public MemoryHierarchy(int workingCapacity = 5, int shortTermCapacity = 20, int longTermCapacity = 200)
    {
        _workingCapacity = workingCapacity;
        _shortTermCapacity = shortTermCapacity;
        _working = new EphemeralMemory(workingCapacity);
        _shortTerm = new EphemeralMemory(shortTermCapacity);
        _longTerm = new EphemeralMemory(longTermCapacity);
    }

    /// <inheritdoc />
    public async Task StoreAsync(Message message, CancellationToken ct = default)
    {
        await _working.StoreAsync(message, ct).ConfigureAwait(false);

        // Promote overflow from working to short-term
        if (_working.Count >= _workingCapacity)
        {
            var toPromote = await _working.RetrieveAsync(1, ct).ConfigureAwait(false);
            if (toPromote.Count > 0)
                await _shortTerm.StoreAsync(toPromote[0], ct).ConfigureAwait(false);
        }

        // Promote overflow from short-term to long-term
        if (_shortTerm.Count >= _shortTermCapacity)
        {
            var toPromote = await _shortTerm.RetrieveAsync(1, ct).ConfigureAwait(false);
            if (toPromote.Count > 0)
                await _longTerm.StoreAsync(toPromote[0], ct).ConfigureAwait(false);
        }
    }

    /// <inheritdoc />
    public async Task<IReadOnlyList<Message>> RetrieveAsync(int count = 10, CancellationToken ct = default)
    {
        // Return most recent from working, then short-term, then long-term
        var working = await _working.RetrieveAsync(count, ct).ConfigureAwait(false);
        if (working.Count >= count) return working;

        var fromShort = await _shortTerm.RetrieveAsync(count - working.Count, ct).ConfigureAwait(false);
        var combined = fromShort.Concat(working).ToList();
        if (combined.Count >= count) return combined;

        var fromLong = await _longTerm.RetrieveAsync(count - combined.Count, ct).ConfigureAwait(false);
        return fromLong.Concat(combined).ToList();
    }

    /// <inheritdoc />
    public async Task ClearAsync(CancellationToken ct = default)
    {
        await _working.ClearAsync(ct).ConfigureAwait(false);
        await _shortTerm.ClearAsync(ct).ConfigureAwait(false);
        await _longTerm.ClearAsync(ct).ConfigureAwait(false);
    }

    /// <summary>Retrieves messages stored only in the working memory tier.</summary>
    public Task<IReadOnlyList<Message>> RetrieveWorkingAsync(int count = 10, CancellationToken ct = default) =>
        _working.RetrieveAsync(count, ct);

    /// <summary>Retrieves messages stored only in the short-term memory tier.</summary>
    public Task<IReadOnlyList<Message>> RetrieveShortTermAsync(int count = 10, CancellationToken ct = default) =>
        _shortTerm.RetrieveAsync(count, ct);

    /// <summary>Retrieves messages stored only in the long-term memory tier.</summary>
    public Task<IReadOnlyList<Message>> RetrieveLongTermAsync(int count = 10, CancellationToken ct = default) =>
        _longTerm.RetrieveAsync(count, ct);
}
