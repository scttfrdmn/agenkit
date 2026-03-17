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
}
