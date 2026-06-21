using System.Text.Json;
using Agenkit.Core;

namespace Agenkit.Adapters;

/// <summary>
/// Normalized, typed token usage for LLM adapter responses.
///
/// Adapters record token counts in <c>Message.Metadata["usage"]</c>, but key
/// names differ between the <c>prompt_tokens</c>/<c>completion_tokens</c>
/// convention and the Anthropic <c>input_tokens</c>/<c>output_tokens</c>
/// convention. <see cref="FromMessage"/> normalizes both into one type so
/// cost-metering and budgeting layers consume a single shape.
///
/// Fields are 0 when the provider does not report them. The cache fields are
/// provider-dependent (e.g. Anthropic prompt caching, including via Bedrock) and
/// are 0 when caching is inactive.
///
/// Mirrors the Go reference (<c>agenkit-go/adapter/llm/usage.go</c>).
/// </summary>
public record TokenUsage(
    long PromptTokens,
    long CompletionTokens,
    long TotalTokens,
    long CacheReadTokens,
    long CacheCreationTokens)
{
    /// <summary>
    /// Extracts normalized token usage from an adapter response message.
    /// Reads the <c>Metadata["usage"]</c> entry, accepting either a nested
    /// dictionary or a <see cref="JsonElement"/> object, and normalizing both
    /// key conventions plus the cache keys (normalized and raw provider aliases).
    /// </summary>
    /// <returns>The usage, or <c>null</c> when no usage metadata is present.
    /// When <c>total_tokens</c> is absent it is derived as prompt + completion.</returns>
    public static TokenUsage? FromMessage(Message? message)
    {
        if (message?.Metadata is null || !message.Metadata.TryGetValue("usage", out var raw))
            return null;

        var lookup = MakeLookup(raw);
        if (lookup is null)
            return null;

        long Pick(params string[] keys)
        {
            foreach (var key in keys)
            {
                var v = lookup(key);
                if (v.HasValue)
                    return v.Value;
            }
            return 0;
        }

        var prompt = Pick("prompt_tokens", "input_tokens");
        var completion = Pick("completion_tokens", "output_tokens");
        var total = Pick("total_tokens");
        if (total == 0)
            total = prompt + completion;

        return new TokenUsage(
            prompt,
            completion,
            total,
            Pick("cache_read_tokens", "cache_read_input_tokens"),
            Pick("cache_creation_tokens", "cache_creation_input_tokens", "cache_write_tokens"));
    }

    /// <summary>
    /// Builds a key→long lookup over the usage value, handling both a plain
    /// dictionary (counts stored directly) and a JsonElement object (raw parse).
    /// Returns null when the value is neither.
    /// </summary>
    private static Func<string, long?>? MakeLookup(object raw)
    {
        switch (raw)
        {
            case JsonElement json when json.ValueKind == JsonValueKind.Object:
                return key =>
                    json.TryGetProperty(key, out var el) && el.ValueKind == JsonValueKind.Number
                        ? el.GetInt64()
                        : null;
            case IReadOnlyDictionary<string, object> dict:
                return key => dict.TryGetValue(key, out var v) ? ToLong(v) : null;
            default:
                return null;
        }
    }

    /// <summary>Coerce a numeric value to long; null for non-numbers.</summary>
    private static long? ToLong(object? v) => v switch
    {
        long l => l,
        int i => i,
        short s => s,
        byte b => b,
        double d => (long)d,
        float f => (long)f,
        JsonElement je when je.ValueKind == JsonValueKind.Number => je.GetInt64(),
        _ => null
    };
}
