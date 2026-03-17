using Agenkit.Core;

namespace Agenkit.Memory.Strategies;

/// <summary>
/// Returns the N most recent messages (sliding window).
/// </summary>
public class SlidingWindowStrategy
{
    private readonly int _windowSize;

    /// <summary>Creates a SlidingWindowStrategy.</summary>
    public SlidingWindowStrategy(int windowSize = 10)
    {
        _windowSize = windowSize > 0 ? windowSize : 10;
    }

    /// <summary>Applies the sliding window to a list of messages.</summary>
    public IReadOnlyList<Message> Apply(IReadOnlyList<Message> messages)
    {
        if (messages.Count <= _windowSize) return messages;
        return messages.Skip(messages.Count - _windowSize).ToList();
    }
}
