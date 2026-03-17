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
}
