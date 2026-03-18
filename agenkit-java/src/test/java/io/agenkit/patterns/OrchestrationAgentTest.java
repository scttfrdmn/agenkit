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

    @Test
    void getNameReturnsName() {
        OrchestrationAgent agent = new OrchestrationAgent("my-orch",
                List.of(new MockAgent("a")), OrchestrationAgent.Mode.SEQUENTIAL);
        assertThat(agent.getName()).isEqualTo("my-orch");
    }

    @Test
    void getCapabilitiesIncludesOrchestration() {
        OrchestrationAgent agent = new OrchestrationAgent("orch",
                List.of(new MockAgent("a")), OrchestrationAgent.Mode.SEQUENTIAL);
        assertThat(agent.getCapabilities()).contains("orchestration");
    }

    @Test
    void introspectReturnsAgentName() {
        OrchestrationAgent agent = new OrchestrationAgent("orch-z",
                List.of(new MockAgent("a")), OrchestrationAgent.Mode.SEQUENTIAL);
        var result = agent.introspect();
        assertThat(result.getAgentName()).isEqualTo("orch-z");
    }

    @Test
    void processReturnsAssistantRole() throws Exception {
        MockAgent a = new MockAgent("a", "output");
        OrchestrationAgent agent = new OrchestrationAgent("orch",
                List.of(a), OrchestrationAgent.Mode.SEQUENTIAL);

        Message response = agent.process(Message.of("user", "go")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void singleAgentSequential() throws Exception {
        MockAgent solo = new MockAgent("solo", "solo result");
        OrchestrationAgent agent = new OrchestrationAgent("orch",
                List.of(solo), OrchestrationAgent.Mode.SEQUENTIAL);

        Message response = agent.process(Message.of("user", "task")).get();

        assertThat(response.contentString()).isEqualTo("solo result");
    }

    @Test
    void introspectReportsAgentCount() {
        MockAgent a = new MockAgent("a");
        MockAgent b = new MockAgent("b");
        OrchestrationAgent agent = new OrchestrationAgent("orch",
                List.of(a, b), OrchestrationAgent.Mode.PARALLEL);

        var result = agent.introspect();
        assertThat(result.getState()).containsEntry("agentCount", 2);
    }

    @Test
    void parallelWithSingleAgent() throws Exception {
        MockAgent solo = new MockAgent("solo", "parallel solo");
        OrchestrationAgent agent = new OrchestrationAgent("orch",
                List.of(solo), OrchestrationAgent.Mode.PARALLEL);

        Message response = agent.process(Message.of("user", "go")).get();

        assertThat(response.contentString()).contains("parallel solo");
        assertThat(response.getMetadata()).containsEntry("agent_count", 1);
    }
}
