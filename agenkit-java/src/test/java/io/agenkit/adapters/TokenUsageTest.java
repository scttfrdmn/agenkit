package io.agenkit.adapters;

import io.agenkit.core.Message;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;

class TokenUsageTest {

    private static Message msgWith(Map<String, Object> usage) {
        return Message.of("assistant", "hi").withMetadata("usage", usage);
    }

    @Test
    void emptyWhenNoUsage() {
        assertThat(TokenUsage.fromMessage(null)).isEmpty();
        assertThat(TokenUsage.fromMessage(Message.of("assistant", "hi"))).isEmpty();
    }

    @Test
    void promptCompletionConvention() {
        Optional<TokenUsage> u = TokenUsage.fromMessage(msgWith(
                Map.of("prompt_tokens", 10, "completion_tokens", 5, "total_tokens", 15)));
        assertThat(u).isPresent();
        assertThat(u.get().promptTokens()).isEqualTo(10);
        assertThat(u.get().completionTokens()).isEqualTo(5);
        assertThat(u.get().totalTokens()).isEqualTo(15);
    }

    @Test
    void anthropicInputOutputConventionDerivesTotal() {
        Optional<TokenUsage> u = TokenUsage.fromMessage(msgWith(
                Map.of("input_tokens", 30, "output_tokens", 7)));
        assertThat(u).isPresent();
        assertThat(u.get().promptTokens()).isEqualTo(30);
        assertThat(u.get().completionTokens()).isEqualTo(7);
        assertThat(u.get().totalTokens()).isEqualTo(37);
    }

    @Test
    void normalizedCacheKeys() {
        Optional<TokenUsage> u = TokenUsage.fromMessage(msgWith(Map.of(
                "prompt_tokens", 1000, "completion_tokens", 50, "total_tokens", 1050,
                "cache_read_tokens", 900, "cache_creation_tokens", 100)));
        assertThat(u).isPresent();
        assertThat(u.get().cacheReadTokens()).isEqualTo(900);
        assertThat(u.get().cacheCreationTokens()).isEqualTo(100);
    }

    @Test
    void rawProviderCacheAliases() {
        Optional<TokenUsage> u = TokenUsage.fromMessage(msgWith(Map.of(
                "input_tokens", 20, "output_tokens", 4,
                "cache_read_input_tokens", 15, "cache_creation_input_tokens", 5)));
        assertThat(u).isPresent();
        assertThat(u.get()).isEqualTo(new TokenUsage(20, 4, 24, 15, 5));
    }

    @Test
    void ignoresNonNumeric() {
        Optional<TokenUsage> u = TokenUsage.fromMessage(msgWith(
                Map.of("prompt_tokens", "x", "completion_tokens", 5)));
        assertThat(u).isPresent();
        assertThat(u.get().promptTokens()).isEqualTo(0);
        assertThat(u.get().completionTokens()).isEqualTo(5);
    }
}
