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

    @Test
    void processReturnsAssistantRole() throws Exception {
        AtomicInteger call = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages -> {
            int n = call.incrementAndGet();
            if (n == 1) return "1. Step one";
            return "done";
        });
        PlanningAgent agent = new PlanningAgent("planner", llm);

        Message response = agent.process(Message.of("user", "plan something")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void getNameReturnsName() {
        PlanningAgent agent = new PlanningAgent("my-planner", new MockLlmClient());
        assertThat(agent.getName()).isEqualTo("my-planner");
    }

    @Test
    void introspectReturnsAgentName() {
        PlanningAgent agent = new PlanningAgent("plan-x", new MockLlmClient());
        var result = agent.introspect();
        assertThat(result.getAgentName()).isEqualTo("plan-x");
    }

    @Test
    void introspectStateHasPlanKey() throws Exception {
        AtomicInteger call = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages -> {
            int n = call.incrementAndGet();
            if (n == 1) return "1. Do it";
            return "done";
        });
        PlanningAgent agent = new PlanningAgent("planner", llm);
        agent.process(Message.of("user", "go")).get();

        var result = agent.introspect();
        assertThat(result.getState()).containsKey("lastPlanSteps");
    }

    @Test
    void emptyPlanHandled() throws Exception {
        AtomicInteger call = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages -> {
            int n = call.incrementAndGet();
            if (n == 1) return "";
            return "nothing to do";
        });
        PlanningAgent agent = new PlanningAgent("planner", llm);

        Message response = agent.process(Message.of("user", "empty plan")).get();

        assertThat(response).isNotNull();
    }

    @Test
    void planStepsMetadata() throws Exception {
        AtomicInteger call = new AtomicInteger(0);
        MockLlmClient llm = new MockLlmClient(messages -> {
            int n = call.incrementAndGet();
            if (n == 1) return "1. Step A\n2. Step B";
            return "completed step " + n;
        });
        PlanningAgent agent = new PlanningAgent("planner", llm);

        Message response = agent.process(Message.of("user", "do tasks")).get();

        assertThat(response.getMetadata()).containsKey("plan_steps");
    }

    @Test
    void multipleCallsWork() throws Exception {
        MockLlmClient llm = new MockLlmClient(messages -> "1. Only step");
        PlanningAgent agent = new PlanningAgent("planner", llm);

        Message first = agent.process(Message.of("user", "first task")).get();
        Message second = agent.process(Message.of("user", "second task")).get();

        assertThat(first).isNotNull();
        assertThat(second).isNotNull();
    }
}
