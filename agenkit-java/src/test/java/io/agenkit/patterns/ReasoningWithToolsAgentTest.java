package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.core.ToolResult;
import io.agenkit.helpers.MockLlmClient;
import io.agenkit.helpers.MockTool;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.*;

class ReasoningWithToolsAgentTest {

    @Test
    void returnsAnswerDirectly() throws Exception {
        MockLlmClient llm = new MockLlmClient("THINK: I know this\nANSWER: 42");
        ReasoningWithToolsAgent agent = new ReasoningWithToolsAgent("rta", llm, List.of());

        Message response = agent.process(Message.of("user", "What is 6x7?")).get();

        assertThat(response.contentString()).isEqualTo("42");
        assertThat(response.getMetadata()).containsKey("steps");
    }

    @Test
    void usesToolInChain() throws Exception {
        AtomicInteger call = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages -> {
            int n = call.incrementAndGet();
            if (n == 1) return "THINK: need to search\nUSE_TOOL: search INPUT: Paris";
            return "ANSWER: Paris is the capital of France";
        });
        MockTool search = new MockTool("search", "searches for information",
                params -> ToolResult.ok("Paris is a city in France"));

        ReasoningWithToolsAgent agent = new ReasoningWithToolsAgent("rta", llm,
                List.of(search), 5);

        Message response = agent.process(Message.of("user", "capital of France?")).get();

        assertThat(response.contentString()).contains("Paris");
        assertThat(search.getCallCount()).isEqualTo(1);
    }

    @Test
    void getCapabilitiesIncludesChainOfThought() {
        ReasoningWithToolsAgent agent = new ReasoningWithToolsAgent(
                "rta", new MockLlmClient(), List.of());
        assertThat(agent.getCapabilities()).contains("chain_of_thought");
    }

    @Test
    void processReturnsAssistantRole() throws Exception {
        MockLlmClient llm = new MockLlmClient("THINK: done\nANSWER: result");
        ReasoningWithToolsAgent agent = new ReasoningWithToolsAgent("rta", llm, List.of());

        Message response = agent.process(Message.of("user", "question")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void getNameReturnsName() {
        ReasoningWithToolsAgent agent = new ReasoningWithToolsAgent(
                "my-rta", new MockLlmClient(), List.of());
        assertThat(agent.getName()).isEqualTo("my-rta");
    }

    @Test
    void introspectReturnsAgentName() {
        ReasoningWithToolsAgent agent = new ReasoningWithToolsAgent(
                "rta-x", new MockLlmClient(), List.of());
        var result = agent.introspect();
        assertThat(result.getAgentName()).isEqualTo("rta-x");
    }

    @Test
    void introspectReturnsStepState() throws Exception {
        MockLlmClient llm = new MockLlmClient("THINK: ok\nANSWER: done");
        ReasoningWithToolsAgent agent = new ReasoningWithToolsAgent("rta", llm, List.of());
        agent.process(Message.of("user", "hello")).get();

        var result = agent.introspect();
        assertThat(result.getState()).containsKey("maxSteps");
    }

    @Test
    void emptyToolListWorks() throws Exception {
        MockLlmClient llm = new MockLlmClient("THINK: no tools\nANSWER: 42");
        ReasoningWithToolsAgent agent = new ReasoningWithToolsAgent("rta", llm, List.of());

        Message response = agent.process(Message.of("user", "no tool needed")).get();

        assertThat(response.contentString()).isEqualTo("42");
    }

    @Test
    void multipleCallsWork() throws Exception {
        MockLlmClient llm = new MockLlmClient("THINK: thinking\nANSWER: ok");
        ReasoningWithToolsAgent agent = new ReasoningWithToolsAgent("rta", llm, List.of());

        Message first = agent.process(Message.of("user", "first")).get();
        Message second = agent.process(Message.of("user", "second")).get();

        assertThat(first.getRole()).isEqualTo("assistant");
        assertThat(second.getRole()).isEqualTo("assistant");
    }
}
