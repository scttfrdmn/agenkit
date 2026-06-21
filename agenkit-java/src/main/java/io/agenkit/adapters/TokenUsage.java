package io.agenkit.adapters;

import io.agenkit.core.Message;

import java.util.Map;
import java.util.Optional;

/**
 * Normalized, typed token usage for LLM adapter responses.
 *
 * <p>Adapters record token counts in {@code Message.metadata["usage"]} as a map,
 * but key names differ between the {@code prompt_tokens}/{@code completion_tokens}
 * convention and the Anthropic {@code input_tokens}/{@code output_tokens}
 * convention. {@link #fromMessage(Message)} normalizes both into one type so
 * cost-metering and budgeting layers consume a single shape.
 *
 * <p>Fields are {@code 0} when the provider does not report them. The cache
 * fields are provider-dependent (e.g. Anthropic prompt caching, including via
 * Bedrock) and are {@code 0} when caching is inactive.
 *
 * <p>Mirrors the Go reference ({@code agenkit-go/adapter/llm/usage.go}).
 */
public record TokenUsage(
        long promptTokens,
        long completionTokens,
        long totalTokens,
        long cacheReadTokens,
        long cacheCreationTokens) {

    /**
     * Extracts normalized token usage from an adapter response message.
     *
     * <p>Reads the {@code metadata["usage"]} map, normalizing both naming
     * conventions ({@code prompt_tokens}/{@code completion_tokens} and Anthropic's
     * {@code input_tokens}/{@code output_tokens}) and the cache keys
     * ({@code cache_read_tokens}/{@code cache_creation_tokens}, plus the raw
     * provider aliases {@code cache_read_input_tokens}/{@code cache_creation_input_tokens}).
     *
     * @param message the adapter response (may be null)
     * @return the usage, or empty when no usage metadata is present. When
     *     {@code total_tokens} is absent it is derived as prompt + completion.
     */
    public static Optional<TokenUsage> fromMessage(Message message) {
        if (message == null || message.getMetadata() == null) {
            return Optional.empty();
        }
        Object raw = message.getMetadata().get("usage");
        if (!(raw instanceof Map<?, ?> usage)) {
            return Optional.empty();
        }

        long prompt = pick(usage, "prompt_tokens", "input_tokens");
        long completion = pick(usage, "completion_tokens", "output_tokens");
        long total = pick(usage, "total_tokens");
        if (total == 0) {
            total = prompt + completion;
        }
        long cacheRead = pick(usage, "cache_read_tokens", "cache_read_input_tokens");
        long cacheCreation =
                pick(usage, "cache_creation_tokens", "cache_creation_input_tokens", "cache_write_tokens");

        return Optional.of(new TokenUsage(prompt, completion, total, cacheRead, cacheCreation));
    }

    /** Returns the first present key coerced to long, or 0 if none/non-numeric. */
    private static long pick(Map<?, ?> usage, String... keys) {
        for (String key : keys) {
            Object value = usage.get(key);
            if (value instanceof Number number) {
                return number.longValue();
            }
        }
        return 0L;
    }
}
