package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockLlmClient;
import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.*;

class ReflectionAgentTest {

    @Test
    void refinesToBetterResponse() throws Exception {
        AtomicInteger call = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages -> switch (call.incrementAndGet() % 3) {
            case 1 -> "initial response";
            case 2 -> "critique: needs more detail";
            default -> "improved response with detail";
        });

        ReflectionAgent agent = new ReflectionAgent("reflective", llm, 1);
        Message response = agent.process(Message.of("user", "explain something")).get();

        assertThat(response.getMetadata()).containsKey("iterations");
    }

    @Test
    void zeroIterationsReturnsInitial() throws Exception {
        MockLlmClient llm = new MockLlmClient("initial answer");
        ReflectionAgent agent = new ReflectionAgent("reflective", llm, 0);

        Message response = agent.process(Message.of("user", "question")).get();
        assertThat(response.contentString()).isEqualTo("initial answer");
    }

    @Test
    void processReturnsAssistantRole() throws Exception {
        MockLlmClient llm = new MockLlmClient("response");
        ReflectionAgent agent = new ReflectionAgent("reflective", llm, 0);

        Message response = agent.process(Message.of("user", "hello")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void getNameReturnsName() {
        ReflectionAgent agent = new ReflectionAgent("my-reflective", new MockLlmClient(), 1);
        assertThat(agent.getName()).isEqualTo("my-reflective");
    }

    @Test
    void getCapabilitiesIncludesReflection() {
        ReflectionAgent agent = new ReflectionAgent("reflective", new MockLlmClient(), 1);
        assertThat(agent.getCapabilities()).contains("reflection");
    }

    @Test
    void introspectReturnsAgentName() {
        ReflectionAgent agent = new ReflectionAgent("reflect-x", new MockLlmClient(), 1);
        var result = agent.introspect();
        assertThat(result.getAgentName()).isEqualTo("reflect-x");
    }

    @Test
    void introspectStateHasIterationsKey() throws Exception {
        AtomicInteger call = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages ->
                call.incrementAndGet() % 2 == 0 ? "critique" : "response");
        ReflectionAgent agent = new ReflectionAgent("reflective", llm, 1);
        agent.process(Message.of("user", "question")).get();

        var result = agent.introspect();
        assertThat(result.getState()).containsKey("maxIterations");
    }

    @Test
    void twoIterationsWork() throws Exception {
        AtomicInteger call = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages -> switch (call.incrementAndGet() % 3) {
            case 1 -> "draft answer";
            case 2 -> "critique: improve it";
            default -> "final improved answer";
        });
        ReflectionAgent agent = new ReflectionAgent("reflective", llm, 2);

        Message response = agent.process(Message.of("user", "write something")).get();

        assertThat(response).isNotNull();
        assertThat(response.getMetadata()).containsKey("iterations");
    }

    @Test
    void defaultIterationsWork() throws Exception {
        MockLlmClient llm = new MockLlmClient("default iteration response");
        ReflectionAgent agent = new ReflectionAgent("reflective", llm);

        Message response = agent.process(Message.of("user", "question")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }
}
