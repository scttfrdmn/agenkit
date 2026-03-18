package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockLlmClient;
import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.*;

class AutonomousAgentTest {

    @Test
    void completesWhenSignalFound() throws Exception {
        AtomicInteger call = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages ->
                call.incrementAndGet() >= 2 ? "TASK_COMPLETE done!" : "still working...");

        AutonomousAgent agent = new AutonomousAgent("auto", llm, 5, "TASK_COMPLETE");
        Message response = agent.process(Message.of("user", "do something")).get();

        assertThat(response.getMetadata()).containsEntry("completed", true);
    }

    @Test
    void stopsAtMaxIterations() throws Exception {
        MockLlmClient llm = new MockLlmClient("still working...");
        AutonomousAgent agent = new AutonomousAgent("auto", llm, 3, "DONE");

        Message response = agent.process(Message.of("user", "task")).get();

        assertThat(response.getMetadata()).containsEntry("completed", false);
        assertThat(response.getMetadata()).containsEntry("iterations", 3);
    }

    @Test
    void processReturnsAssistantRole() throws Exception {
        MockLlmClient llm = new MockLlmClient("TASK_COMPLETE result");
        AutonomousAgent agent = new AutonomousAgent("auto", llm, 5, "TASK_COMPLETE");

        Message response = agent.process(Message.of("user", "do it")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void getNameReturnsName() {
        AutonomousAgent agent = new AutonomousAgent("my-auto", new MockLlmClient(), 3, "DONE");
        assertThat(agent.getName()).isEqualTo("my-auto");
    }

    @Test
    void getCapabilitiesIncludesAutonomous() {
        AutonomousAgent agent = new AutonomousAgent("auto", new MockLlmClient(), 3, "DONE");
        assertThat(agent.getCapabilities()).contains("autonomous");
    }

    @Test
    void introspectReturnsAgentName() {
        AutonomousAgent agent = new AutonomousAgent("auto-x", new MockLlmClient(), 3, "DONE");
        var result = agent.introspect();
        assertThat(result.getAgentName()).isEqualTo("auto-x");
    }

    @Test
    void introspectReturnsIterationState() throws Exception {
        MockLlmClient llm = new MockLlmClient("still working...");
        AutonomousAgent agent = new AutonomousAgent("auto", llm, 2, "DONE");
        agent.process(Message.of("user", "task")).get();

        var result = agent.introspect();
        assertThat(result.getState()).containsKey("maxIterations");
    }

    @Test
    void emptyInputProcessed() throws Exception {
        MockLlmClient llm = new MockLlmClient("TASK_COMPLETE ok");
        AutonomousAgent agent = new AutonomousAgent("auto", llm, 5, "TASK_COMPLETE");

        Message response = agent.process(Message.of("user", "")).get();

        assertThat(response).isNotNull();
    }

    @Test
    void multipleCallsWork() throws Exception {
        MockLlmClient llm = new MockLlmClient("TASK_COMPLETE done");
        AutonomousAgent agent = new AutonomousAgent("auto", llm, 5, "TASK_COMPLETE");

        Message first = agent.process(Message.of("user", "first task")).get();
        Message second = agent.process(Message.of("user", "second task")).get();

        assertThat(first).isNotNull();
        assertThat(second).isNotNull();
    }
}
