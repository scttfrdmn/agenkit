package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockLlmClient;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class TaskAgentTest {

    @Test
    void completesTaskSuccessfully() throws Exception {
        MockLlmClient llm = new MockLlmClient("task done");
        TaskAgent agent = new TaskAgent("task", llm, "Write a summary");

        Message response = agent.process(Message.of("user", "start")).get();

        assertThat(response.contentString()).isEqualTo("task done");
        assertThat(response.getMetadata()).containsEntry("task_status", "complete");
        assertThat(agent.getStatus()).isEqualTo(TaskAgent.Status.COMPLETE);
    }

    @Test
    void idleAfterReset() throws Exception {
        MockLlmClient llm = new MockLlmClient("done");
        TaskAgent agent = new TaskAgent("task", llm, "task");
        agent.process(Message.of("user", "start")).get();

        agent.reset();

        assertThat(agent.getStatus()).isEqualTo(TaskAgent.Status.IDLE);
    }

    @Test
    void processReturnsAssistantRole() throws Exception {
        MockLlmClient llm = new MockLlmClient("result");
        TaskAgent agent = new TaskAgent("task", llm, "Do something");

        Message response = agent.process(Message.of("user", "start")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void getNameReturnsName() {
        TaskAgent agent = new TaskAgent("my-task", new MockLlmClient(), "task description");
        assertThat(agent.getName()).isEqualTo("my-task");
    }

    @Test
    void getCapabilitiesIncludesTaskManagement() {
        TaskAgent agent = new TaskAgent("task", new MockLlmClient(), "description");
        assertThat(agent.getCapabilities()).contains("task_execution");
    }

    @Test
    void introspectReturnsAgentName() {
        TaskAgent agent = new TaskAgent("task-x", new MockLlmClient(), "description");
        var result = agent.introspect();
        assertThat(result.getAgentName()).isEqualTo("task-x");
    }

    @Test
    void introspectStateHasStatusKey() throws Exception {
        MockLlmClient llm = new MockLlmClient("done");
        TaskAgent agent = new TaskAgent("task", llm, "my task");
        agent.process(Message.of("user", "go")).get();

        var result = agent.introspect();
        assertThat(result.getState()).containsKey("status");
    }

    @Test
    void taskDescriptionInIntrospect() {
        TaskAgent agent = new TaskAgent("task", new MockLlmClient(), "Write a report");
        var result = agent.introspect();
        assertThat(result.getState()).containsKey("task");
    }

    @Test
    void processTwiceAfterReset() throws Exception {
        MockLlmClient llm = new MockLlmClient("completed");
        TaskAgent agent = new TaskAgent("task", llm, "repeatable task");

        agent.process(Message.of("user", "start")).get();
        assertThat(agent.getStatus()).isEqualTo(TaskAgent.Status.COMPLETE);

        agent.reset();
        assertThat(agent.getStatus()).isEqualTo(TaskAgent.Status.IDLE);

        Message second = agent.process(Message.of("user", "start again")).get();
        assertThat(second.getRole()).isEqualTo("assistant");
        assertThat(agent.getStatus()).isEqualTo(TaskAgent.Status.COMPLETE);
    }
}
