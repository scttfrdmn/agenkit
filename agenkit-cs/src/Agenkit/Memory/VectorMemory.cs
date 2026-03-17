using Agenkit.Core;

namespace Agenkit.Memory;

/// <summary>
/// Memory store with simple cosine-similarity retrieval over embedded messages.
/// The default embedder uses bag-of-words character n-grams as a lightweight proxy.
/// </summary>
public class VectorMemory : IMemory
{
    private readonly int _maxMessages;
    private readonly Func<string, float[]> _embedder;
    private readonly List<(Message message, float[] embedding)> _store = new();
    private readonly SemaphoreSlim _lock = new(1, 1);

    /// <summary>Creates a VectorMemory with an optional custom embedder.</summary>
    /// <param name="maxMessages">Maximum stored messages.</param>
    /// <param name="embedder">Optional custom embedding function. Defaults to simple TF bag-of-words.</param>
    public VectorMemory(int maxMessages = 200, Func<string, float[]>? embedder = null)
    {
        _maxMessages = maxMessages > 0 ? maxMessages : 200;
        _embedder = embedder ?? SimpleEmbed;
    }

    /// <inheritdoc />
    public async Task StoreAsync(Message message, CancellationToken ct = default)
    {
        var embedding = _embedder(message.ContentString());
        await _lock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            _store.Add((message, embedding));
            if (_store.Count > _maxMessages)
                _store.RemoveAt(0);
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
            // Return most recent messages (no query vector — sequential fallback)
            var skip = Math.Max(0, _store.Count - count);
            return _store.Skip(skip).Select(x => x.message).ToList();
        }
        finally
        {
            _lock.Release();
        }
    }

    /// <summary>Retrieves the <paramref name="count"/> most similar messages to the given query.</summary>
    public async Task<IReadOnlyList<Message>> RetrieveSimilarAsync(
        string query, int count = 5, CancellationToken ct = default)
    {
        var queryVec = _embedder(query);

        await _lock.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            return _store
                .Select(x => (x.message, score: CosineSimilarity(queryVec, x.embedding)))
                .OrderByDescending(x => x.score)
                .Take(count)
                .Select(x => x.message)
                .ToList();
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
        try { _store.Clear(); }
        finally { _lock.Release(); }
    }

    private static float[] SimpleEmbed(string text)
    {
        // Bag-of-words over character trigrams, dim=64
        const int dim = 64;
        var vec = new float[dim];
        var lower = text.ToLowerInvariant();
        for (int i = 0; i + 2 < lower.Length; i++)
        {
            var h = (lower[i] * 31 * 31 + lower[i + 1] * 31 + lower[i + 2]) % dim;
            vec[Math.Abs(h)]++;
        }
        Normalize(vec);
        return vec;
    }

    private static void Normalize(float[] vec)
    {
        var norm = MathF.Sqrt(vec.Sum(v => v * v));
        if (norm < 1e-8f) return;
        for (int i = 0; i < vec.Length; i++)
            vec[i] /= norm;
    }

    private static float CosineSimilarity(float[] a, float[] b)
    {
        if (a.Length != b.Length) return 0;
        float dot = 0;
        for (int i = 0; i < a.Length; i++)
            dot += a[i] * b[i];
        return dot;
    }
}
