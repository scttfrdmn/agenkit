package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockLlmClient;
import io.agenkit.memory.EphemeralMemory;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class MemoryAugmentedAgentTest {

    @Test
    void storesAndRetrievesMemory() throws Exception {
        EphemeralMemory memory = new EphemeralMemory();
        MockLlmClient llm = new MockLlmClient("answer");
        MemoryAugmentedAgent agent = new MemoryAugmentedAgent("mem-agent", llm, memory);

        agent.process(Message.of("user", "remember: sky is blue")).get();
        agent.process(Message.of("user", "what color is the sky?")).get();

        assertThat(memory.size()).isGreaterThan(0);
    }

    @Test
    void introspectReportsMemorySize() throws Exception {
        EphemeralMemory memory = new EphemeralMemory();
        MockLlmClient llm = new MockLlmClient("ok");
        MemoryAugmentedAgent agent = new MemoryAugmentedAgent("mem", llm, memory);
        agent.process(Message.of("user", "hello")).get();

        var result = agent.introspect();
        assertThat(result.getMemory()).containsKey("size");
    }
}
