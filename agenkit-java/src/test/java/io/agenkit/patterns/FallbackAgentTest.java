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

    private static Agent failingAgent(String name) {
        return new Agent() {
            public String getName() { return name; }
            public List<String> getCapabilities() { return List.of(); }
            public CompletableFuture<Message> process(Message m) {
                return CompletableFuture.failedFuture(new RuntimeException("failed"));
            }
            public IntrospectionResult introspect() {
                return new IntrospectionResult(name, List.of(), null, null, null);
            }
        };
    }

    @Test
    void usesFirstSuccessfulAgent() throws Exception {
        Agent failing = failingAgent("failing");
        MockAgent backup = new MockAgent("backup", "backup response");

        FallbackAgent fallback = new FallbackAgent("fallback", List.of(failing, backup));
        Message response = fallback.process(Message.of("user", "hello")).get();

        assertThat(response.contentString()).isEqualTo("backup response");
        assertThat(response.getMetadata()).containsEntry("used_agent", "backup");
    }

    @Test
    void allFailedReturnsError() throws Exception {
        Agent failing = failingAgent("failing");

        FallbackAgent fallback = new FallbackAgent("fallback", List.of(failing));
        Message response = fallback.process(Message.of("user", "hello")).get();

        assertThat(response.getMetadata()).containsEntry("fallback_exhausted", true);
    }

    @Test
    void getNameReturnsName() {
        FallbackAgent agent = new FallbackAgent("my-fallback", List.of(new MockAgent()));
        assertThat(agent.getName()).isEqualTo("my-fallback");
    }

    @Test
    void getCapabilitiesIncludesFallback() {
        FallbackAgent agent = new FallbackAgent("fallback", List.of(new MockAgent()));
        assertThat(agent.getCapabilities()).contains("fallback");
    }

    @Test
    void introspectReturnsAgentName() {
        FallbackAgent agent = new FallbackAgent("fb-x", List.of(new MockAgent()));
        var result = agent.introspect();
        assertThat(result.getAgentName()).isEqualTo("fb-x");
    }

    @Test
    void firstAgentSucceedsNoFallback() throws Exception {
        MockAgent primary = new MockAgent("primary", "primary result");
        MockAgent backup = new MockAgent("backup", "backup result");

        FallbackAgent fallback = new FallbackAgent("fallback", List.of(primary, backup));
        Message response = fallback.process(Message.of("user", "hello")).get();

        assertThat(response.contentString()).isEqualTo("primary result");
        assertThat(response.getMetadata()).containsEntry("used_agent", "primary");
    }

    @Test
    void processReturnsAssistantRole() throws Exception {
        MockAgent agent = new MockAgent("ok-agent", "success");
        FallbackAgent fallback = new FallbackAgent("fallback", List.of(agent));

        Message response = fallback.process(Message.of("user", "test")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void introspectListsAgents() {
        MockAgent a1 = new MockAgent("agent1");
        MockAgent a2 = new MockAgent("agent2");
        FallbackAgent fallback = new FallbackAgent("fallback", List.of(a1, a2));

        var result = fallback.introspect();
        assertThat(result.getState()).containsKey("chainLength");
    }

    @Test
    void emptyAgentListHandled() throws Exception {
        FallbackAgent fallback = new FallbackAgent("fallback", List.of());
        Message response = fallback.process(Message.of("user", "hello")).get();

        assertThat(response.getMetadata()).containsEntry("fallback_exhausted", true);
    }
}
