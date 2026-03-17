package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import io.agenkit.helpers.MockLlmClient;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class SupervisorAgentTest {

    @Test
    void supervisorDelegatesWork() throws Exception {
        MockAgent worker1 = new MockAgent("worker1", "worker1 result");
        MockAgent worker2 = new MockAgent("worker2", "worker2 result");
        MockLlmClient llm = new MockLlmClient(
                messages -> "worker1: do task A\nworker2: do task B");

        SupervisorAgent supervisor = new SupervisorAgent("supervisor", llm,
                List.of(worker1, worker2));

        Message response = supervisor.process(Message.of("user", "do a complex task")).get();

        assertThat(response.contentString()).isNotEmpty();
        assertThat(response.getMetadata()).containsKey("supervisor");
    }

    @Test
    void getCapabilitiesIncludesDelegation() {
        SupervisorAgent agent = new SupervisorAgent("sup", new MockLlmClient(),
                List.of(new MockAgent()));
        assertThat(agent.getCapabilities()).contains("supervision");
    }

    @Test
    void introspectListsWorkers() {
        MockAgent w1 = new MockAgent("worker1");
        MockAgent w2 = new MockAgent("worker2");
        SupervisorAgent supervisor = new SupervisorAgent("sup", new MockLlmClient(),
                List.of(w1, w2));

        var result = supervisor.introspect();
        assertThat(result.getTools()).containsExactlyInAnyOrder("worker1", "worker2");
    }
}
