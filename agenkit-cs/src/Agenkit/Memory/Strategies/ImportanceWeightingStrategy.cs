using Agenkit.Core;

namespace Agenkit.Memory.Strategies;

/// <summary>
/// Selects messages by importance score stored in metadata.
/// Falls back to recency when scores are equal.
/// </summary>
public class ImportanceWeightingStrategy
{
    private readonly int _topK;
    private readonly string _scoreKey;

    /// <summary>Creates an ImportanceWeightingStrategy.</summary>
    /// <param name="topK">Number of messages to retain.</param>
    /// <param name="scoreKey">Metadata key for the importance score (default: "importance").</param>
    public ImportanceWeightingStrategy(int topK = 10, string scoreKey = "importance")
    {
        _topK = topK > 0 ? topK : 10;
        _scoreKey = scoreKey;
    }

    /// <summary>Returns the top-K messages by importance score.</summary>
    public IReadOnlyList<Message> Apply(IReadOnlyList<Message> messages)
    {
        return messages
            .Select((m, idx) => (message: m, idx, score: GetScore(m)))
            .OrderByDescending(x => x.score)
            .ThenByDescending(x => x.idx) // recency tiebreak
            .Take(_topK)
            .OrderBy(x => x.idx) // restore chronological order
            .Select(x => x.message)
            .ToList();
    }

    private double GetScore(Message message)
    {
        if (message.Metadata is null) return 0;
        if (!message.Metadata.TryGetValue(_scoreKey, out var raw)) return 0;
        return raw switch
        {
            double d => d,
            float f => f,
            int i => i,
            long l => l,
            string s when double.TryParse(s, out var d) => d,
            _ => 0
        };
    }
}
