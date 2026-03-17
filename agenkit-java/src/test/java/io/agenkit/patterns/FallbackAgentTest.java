package io.agenkit.patterns;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.*;

class FallbackAgentTest {

    @Test
    void usesFirstSuccessfulAgent() throws Exception {
        Agent failing = new Agent() {
            public String getName() { return "failing"; }
            public List<String> getCapabilities() { return List.of(); }
            public CompletableFuture<Message> process(Message m) {
                return CompletableFuture.failedFuture(new RuntimeException("failed"));
            }
            public IntrospectionResult introspect() {
                return new IntrospectionResult("failing", List.of(), null, null, null);
            }
        };
        MockAgent backup = new MockAgent("backup", "backup response");

        FallbackAgent fallback = new FallbackAgent("fallback", List.of(failing, backup));
        Message response = fallback.process(Message.of("user", "hello")).get();

        assertThat(response.contentString()).isEqualTo("backup response");
        assertThat(response.getMetadata()).containsEntry("used_agent", "backup");
    }

    @Test
    void allFailedReturnsError() throws Exception {
        Agent failing = new Agent() {
            public String getName() { return "failing"; }
            public List<String> getCapabilities() { return List.of(); }
            public CompletableFuture<Message> process(Message m) {
                return CompletableFuture.failedFuture(new RuntimeException("failed"));
            }
            public IntrospectionResult introspect() {
                return new IntrospectionResult("failing", List.of(), null, null, null);
            }
        };

        FallbackAgent fallback = new FallbackAgent("fallback", List.of(failing));
        Message response = fallback.process(Message.of("user", "hello")).get();

        assertThat(response.getMetadata()).containsEntry("fallback_exhausted", true);
    }
}
