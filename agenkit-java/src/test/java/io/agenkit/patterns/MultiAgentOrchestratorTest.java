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

    @Test
    void processReturnsAssistantRole() throws Exception {
        MockAgent agent = new MockAgent("worker", "done");
        MockLlmClient llm = new MockLlmClient("AGENT: worker\nTASK: do work");

        MultiAgentOrchestrator orchestrator = new MultiAgentOrchestrator(
                "orch", llm, Map.of("worker", agent));

        Message response = orchestrator.process(Message.of("user", "work")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void getNameReturnsName() {
        MultiAgentOrchestrator orch = new MultiAgentOrchestrator(
                "my-orch", new MockLlmClient(), Map.of("a", new MockAgent("a")));
        assertThat(orch.getName()).isEqualTo("my-orch");
    }

    @Test
    void introspectReturnsAgentName() {
        MultiAgentOrchestrator orch = new MultiAgentOrchestrator(
                "orch-x", new MockLlmClient(), Map.of("a", new MockAgent("a")));
        var result = orch.introspect();
        assertThat(result.getAgentName()).isEqualTo("orch-x");
    }

    @Test
    void orchestratorCapabilityListed() {
        MultiAgentOrchestrator orch = new MultiAgentOrchestrator(
                "orch", new MockLlmClient(), Map.of("a", new MockAgent("a")));
        assertThat(orch.getCapabilities()).isNotEmpty();
    }

    @Test
    void emptyAgentMapHandled() throws Exception {
        MockLlmClient llm = new MockLlmClient("AGENT: nobody\nTASK: something");
        MultiAgentOrchestrator orch = new MultiAgentOrchestrator("orch", llm, Map.of());

        Message response = orch.process(Message.of("user", "anything")).get();

        assertThat(response).isNotNull();
    }

    @Test
    void multipleCallsWork() throws Exception {
        MockAgent worker = new MockAgent("worker", "result");
        MockLlmClient llm = new MockLlmClient("AGENT: worker\nTASK: task");

        MultiAgentOrchestrator orch = new MultiAgentOrchestrator(
                "orch", llm, Map.of("worker", worker));

        Message first = orch.process(Message.of("user", "first")).get();
        Message second = orch.process(Message.of("user", "second")).get();

        assertThat(first).isNotNull();
        assertThat(second).isNotNull();
    }
}
