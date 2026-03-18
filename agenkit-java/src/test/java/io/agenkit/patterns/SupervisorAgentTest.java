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
        MockAgent w1 = new MockAgent("worker1", "result1");
        MockAgent w2 = new MockAgent("worker2", "result2");
        SupervisorAgent supervisor = new SupervisorAgent("sup", new MockLlmClient(),
                List.of(w1, w2));

        var result = supervisor.introspect();
        assertThat(result.getTools()).containsExactlyInAnyOrder("worker1", "worker2");
    }

    @Test
    void processReturnsAssistantRole() throws Exception {
        MockAgent worker = new MockAgent("worker", "done");
        MockLlmClient llm = new MockLlmClient("worker: do the task");

        SupervisorAgent supervisor = new SupervisorAgent("sup", llm, List.of(worker));
        Message response = supervisor.process(Message.of("user", "task")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void getNameReturnsName() {
        SupervisorAgent agent = new SupervisorAgent("my-supervisor", new MockLlmClient(),
                List.of(new MockAgent()));
        assertThat(agent.getName()).isEqualTo("my-supervisor");
    }

    @Test
    void introspectReturnsAgentName() {
        SupervisorAgent supervisor = new SupervisorAgent("sup-x", new MockLlmClient(),
                List.of(new MockAgent("w")));
        var result = supervisor.introspect();
        assertThat(result.getAgentName()).isEqualTo("sup-x");
    }

    @Test
    void singleWorkerSupervisor() throws Exception {
        MockAgent worker = new MockAgent("solo-worker", "solo result");
        MockLlmClient llm = new MockLlmClient("solo-worker: do everything");

        SupervisorAgent supervisor = new SupervisorAgent("sup", llm, List.of(worker));
        Message response = supervisor.process(Message.of("user", "do it all")).get();

        assertThat(response.contentString()).isNotEmpty();
    }

    @Test
    void multipleCallsWork() throws Exception {
        MockAgent worker = new MockAgent("worker", "result");
        MockLlmClient llm = new MockLlmClient("worker: do task");

        SupervisorAgent supervisor = new SupervisorAgent("sup", llm, List.of(worker));

        Message first = supervisor.process(Message.of("user", "first task")).get();
        Message second = supervisor.process(Message.of("user", "second task")).get();

        assertThat(first).isNotNull();
        assertThat(second).isNotNull();
    }

    @Test
    void supervisorCapabilityListed() {
        SupervisorAgent supervisor = new SupervisorAgent("sup", new MockLlmClient(),
                List.of(new MockAgent("w")));
        assertThat(supervisor.getCapabilities()).contains("supervision");
    }
}
