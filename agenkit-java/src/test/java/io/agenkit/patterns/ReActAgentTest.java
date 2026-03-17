package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockLlmClient;
import io.agenkit.helpers.MockTool;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.*;

class ReActAgentTest {

    @Test
    void returnsFinalAnswerImmediately() throws Exception {
        MockLlmClient llm = new MockLlmClient("Thought: I know the answer\nFinal Answer: 42");
        ReActAgent agent = new ReActAgent("react", llm, List.of());

        Message response = agent.process(Message.of("user", "What is 6x7?")).get();

        assertThat(response.contentString()).isEqualTo("42");
        assertThat(response.getMetadata()).containsEntry("stop_reason", "final_answer");
    }

    @Test
    void executeToolOnAction() throws Exception {
        AtomicInteger callCount = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages -> {
            int call = callCount.incrementAndGet();
            if (call == 1) {
                return "Thought: I need to calculate\nAction: calculator\nAction Input: 6*7";
            }
            return "Thought: Got result\nFinal Answer: The answer is 42";
        });
        MockTool calculator = new MockTool("calculator", "performs calculations",
                params -> io.agenkit.core.ToolResult.ok("42"));

        ReActAgent agent = new ReActAgent("react", llm, List.of(calculator));
        Message response = agent.process(Message.of("user", "What is 6*7?")).get();

        assertThat(response.contentString()).contains("42");
        assertThat(calculator.getCallCount()).isEqualTo(1);
    }

    @Test
    void stopsAtMaxSteps() throws Exception {
        MockLlmClient llm = new MockLlmClient("Thought: thinking\nAction: unknown_tool\nAction Input: something");
        ReActAgent agent = new ReActAgent("react", llm, List.of(), 3, false);

        Message response = agent.process(Message.of("user", "question")).get();

        assertThat(response.getMetadata()).containsEntry("stop_reason", "max_steps");
    }

    @Test
    void introspectReturnsToolNames() {
        MockTool tool1 = new MockTool("tool1");
        MockTool tool2 = new MockTool("tool2");
        ReActAgent agent = new ReActAgent("react", new MockLlmClient(), List.of(tool1, tool2));

        var result = agent.introspect();
        assertThat(result.getTools()).containsExactlyInAnyOrder("tool1", "tool2");
    }
}
