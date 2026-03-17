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
}
