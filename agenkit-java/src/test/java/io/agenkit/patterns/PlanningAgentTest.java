package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockLlmClient;
import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.*;

class PlanningAgentTest {

    @Test
    void executesStepsFromPlan() throws Exception {
        AtomicInteger call = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages -> {
            int n = call.incrementAndGet();
            if (n == 1) return "1. Research the topic\n2. Write a summary\n3. Review";
            return "Done: step " + n;
        });

        PlanningAgent agent = new PlanningAgent("planner", llm);
        Message response = agent.process(Message.of("user", "Write a report")).get();

        assertThat(response.contentString()).contains("Executed");
        assertThat(response.getMetadata()).containsKey("plan_steps");
    }

    @Test
    void getCapabilitiesIncludesPlanning() {
        PlanningAgent agent = new PlanningAgent("planner", new MockLlmClient());
        assertThat(agent.getCapabilities()).contains("planning");
    }
}
