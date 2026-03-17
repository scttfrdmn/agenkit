package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import io.agenkit.helpers.MockLlmClient;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.*;

class MultiAgentOrchestratorTest {

    @Test
    void routesToCorrectAgent() throws Exception {
        MockAgent analyst = new MockAgent("analyst", "analysis result");
        MockAgent writer = new MockAgent("writer", "written content");

        MockLlmClient llm = new MockLlmClient("AGENT: analyst\nTASK: analyze the data");

        MultiAgentOrchestrator orchestrator = new MultiAgentOrchestrator(
                "orchestrator", llm, Map.of("analyst", analyst, "writer", writer));

        Message response = orchestrator.process(Message.of("user", "analyze this")).get();

        assertThat(response.contentString()).isEqualTo("analysis result");
        assertThat(response.getMetadata()).containsKey("orchestrator");
    }

    @Test
    void fallsBackToFirstAgentWhenNoMatch() throws Exception {
        MockAgent fallback = new MockAgent("fallback", "fallback response");
        MockLlmClient llm = new MockLlmClient("AGENT: unknown\nTASK: something");

        MultiAgentOrchestrator orchestrator = new MultiAgentOrchestrator(
                "orchestrator", llm, Map.of("fallback", fallback));

        Message response = orchestrator.process(Message.of("user", "task")).get();
        assertThat(response.contentString()).isEqualTo("fallback response");
    }

    @Test
    void introspectListsAgentCount() {
        MockAgent a = new MockAgent("a");
        MockAgent b = new MockAgent("b");
        MultiAgentOrchestrator orch = new MultiAgentOrchestrator(
                "orch", new MockLlmClient(), Map.of("a", a, "b", b));

        var result = orch.introspect();
        assertThat(result.getState()).containsEntry("agentCount", 2);
    }
}
