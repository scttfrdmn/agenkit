package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class OrchestrationAgentTest {

    @Test
    void sequentialPassesOutputToNext() throws Exception {
        MockAgent first = new MockAgent("first", "FIRST");
        MockAgent second = new MockAgent("second", msg -> "got: " + msg.contentString());

        OrchestrationAgent agent = new OrchestrationAgent("orch",
                List.of(first, second), OrchestrationAgent.Mode.SEQUENTIAL);

        Message response = agent.process(Message.of("user", "hello")).get();
        assertThat(response.contentString()).isEqualTo("got: FIRST");
    }

    @Test
    void parallelAggregatesResults() throws Exception {
        MockAgent a1 = new MockAgent("a1", "result1");
        MockAgent a2 = new MockAgent("a2", "result2");

        OrchestrationAgent agent = new OrchestrationAgent("orch",
                List.of(a1, a2), OrchestrationAgent.Mode.PARALLEL);

        Message response = agent.process(Message.of("user", "hello")).get();
        assertThat(response.contentString()).contains("result1").contains("result2");
        assertThat(response.getMetadata()).containsEntry("agent_count", 2);
    }
}
