using Agenkit.Core;

namespace Agenkit.Memory.Strategies;

/// <summary>
/// Compresses older messages into a summary when the buffer exceeds capacity.
/// The summarizer is supplied as a delegate that receives a list of messages
/// and returns a single summary message.
/// </summary>
public class SummarizationStrategy
{
    private readonly int _maxMessages;
    private readonly Func<IReadOnlyList<Message>, Task<Message>> _summarizer;

    /// <summary>Creates a SummarizationStrategy.</summary>
    /// <param name="maxMessages">Buffer size before summarization is triggered.</param>
    /// <param name="summarizer">Async function that summarizes a list of messages.</param>
    public SummarizationStrategy(int maxMessages, Func<IReadOnlyList<Message>, Task<Message>> summarizer)
    {
        _maxMessages = maxMessages > 0 ? maxMessages : 20;
        _summarizer = summarizer;
    }

    /// <summary>
    /// Ensures the buffer stays within capacity by summarizing older messages.
    /// Returns the (possibly updated) message list.
    /// </summary>
    public async Task<IReadOnlyList<Message>> ApplyAsync(
        IReadOnlyList<Message> messages, CancellationToken ct = default)
    {
        if (messages.Count <= _maxMessages) return messages;

        // Split into old (to summarize) and recent (to keep verbatim)
        var keepCount = _maxMessages / 2;
        var toSummarize = messages.Take(messages.Count - keepCount).ToList();
        var keep = messages.Skip(messages.Count - keepCount).ToList();

        var summary = await _summarizer(toSummarize).ConfigureAwait(false);
        return new[] { summary }.Concat(keep).ToList();
    }
}
