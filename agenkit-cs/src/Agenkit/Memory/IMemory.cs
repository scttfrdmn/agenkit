using Agenkit.Core;

namespace Agenkit.Memory;

/// <summary>
/// Abstraction for agent memory stores.
/// </summary>
public interface IMemory
{
    /// <summary>Stores a message in memory.</summary>
    Task StoreAsync(Message message, CancellationToken ct = default);

    /// <summary>Retrieves the most recent messages up to <paramref name="count"/>.</summary>
    Task<IReadOnlyList<Message>> RetrieveAsync(int count = 10, CancellationToken ct = default);

    /// <summary>Clears all stored messages.</summary>
    Task ClearAsync(CancellationToken ct = default);
}
