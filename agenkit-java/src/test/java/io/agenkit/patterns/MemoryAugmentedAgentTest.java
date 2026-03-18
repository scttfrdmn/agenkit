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

    @Test
    void processReturnsAssistantRole() throws Exception {
        EphemeralMemory memory = new EphemeralMemory();
        MockLlmClient llm = new MockLlmClient("response");
        MemoryAugmentedAgent agent = new MemoryAugmentedAgent("mem", llm, memory);

        Message response = agent.process(Message.of("user", "hello")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void getNameReturnsName() {
        EphemeralMemory memory = new EphemeralMemory();
        MemoryAugmentedAgent agent = new MemoryAugmentedAgent("my-mem", new MockLlmClient(), memory);
        assertThat(agent.getName()).isEqualTo("my-mem");
    }

    @Test
    void getCapabilitiesIncludesMemory() {
        EphemeralMemory memory = new EphemeralMemory();
        MemoryAugmentedAgent agent = new MemoryAugmentedAgent("mem", new MockLlmClient(), memory);
        assertThat(agent.getCapabilities()).contains("memory");
    }

    @Test
    void introspectReturnsAgentName() {
        EphemeralMemory memory = new EphemeralMemory();
        MemoryAugmentedAgent agent = new MemoryAugmentedAgent("mem-z", new MockLlmClient(), memory);
        var result = agent.introspect();
        assertThat(result.getAgentName()).isEqualTo("mem-z");
    }

    @Test
    void memoryGrowsWithCalls() throws Exception {
        EphemeralMemory memory = new EphemeralMemory();
        MockLlmClient llm = new MockLlmClient("ok");
        MemoryAugmentedAgent agent = new MemoryAugmentedAgent("mem", llm, memory);

        agent.process(Message.of("user", "first fact")).get();
        int sizeAfterOne = memory.size();
        agent.process(Message.of("user", "second fact")).get();
        int sizeAfterTwo = memory.size();

        assertThat(sizeAfterTwo).isGreaterThanOrEqualTo(sizeAfterOne);
    }

    @Test
    void defaultMemoryWorks() throws Exception {
        MockLlmClient llm = new MockLlmClient("default response");
        MemoryAugmentedAgent agent = new MemoryAugmentedAgent("mem", llm, new EphemeralMemory());

        Message response = agent.process(Message.of("user", "hello")).get();

        assertThat(response).isNotNull();
        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void clearMemoryBetweenSessions() throws Exception {
        EphemeralMemory memory = new EphemeralMemory();
        MockLlmClient llm = new MockLlmClient("ok");
        MemoryAugmentedAgent agent = new MemoryAugmentedAgent("mem", llm, memory);

        agent.process(Message.of("user", "remember this")).get();
        assertThat(memory.size()).isGreaterThan(0);

        memory.clear();
        assertThat(memory.size()).isEqualTo(0);
    }
}
