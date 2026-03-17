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
}
