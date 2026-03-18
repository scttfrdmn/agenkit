package io.agenkit.properties;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import net.jqwik.api.*;
import net.jqwik.api.constraints.StringLength;

import static org.assertj.core.api.Assertions.*;

class AgentPropertyTest {

    @Property
    void mockAgentNameRoundTrips(@ForAll @StringLength(min = 1, max = 30) String name) {
        MockAgent agent = new MockAgent(name, "response");
        assertThat(agent.getName()).isEqualTo(name);
    }

    @Property
    void mockAgentAlwaysReturnsAssistantRole(
            @ForAll @StringLength(min = 1, max = 50) String content) throws Exception {
        MockAgent agent = new MockAgent("agent", "fixed");
        Message response = agent.process(Message.of("user", content)).get();
        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Property
    void mockAgentResponseIsNotNull(
            @ForAll @StringLength(min = 0, max = 100) String input) throws Exception {
        MockAgent agent = new MockAgent("agent", "something");
        Message response = agent.process(Message.of("user", input)).get();
        assertThat(response).isNotNull();
        assertThat(response.contentString()).isNotNull();
    }

    @Property
    void mockAgentTracksReceivedMessages(
            @ForAll @StringLength(min = 1, max = 40) String content) throws Exception {
        MockAgent agent = new MockAgent("tracker", "ok");
        agent.process(Message.of("user", content)).get();
        assertThat(agent.getReceived()).hasSize(1);
        assertThat(agent.getReceived().get(0).contentString()).isEqualTo(content);
    }

    @Property
    void mockAgentCapabilitiesNonNull(@ForAll @StringLength(min = 1, max = 20) String name) {
        MockAgent agent = new MockAgent(name, "ok");
        assertThat(agent.getCapabilities()).isNotNull();
        assertThat(agent.getCapabilities()).contains("mock");
    }

    @Property
    void introspectAgentNameMatchesGetName(@ForAll @StringLength(min = 1, max = 30) String name) {
        MockAgent agent = new MockAgent(name, "response");
        assertThat(agent.introspect().getAgentName()).isEqualTo(name);
    }

    @Property
    void introspectCapabilitiesNeverNull(@ForAll @StringLength(min = 1, max = 20) String name) {
        MockAgent agent = new MockAgent(name, "ok");
        assertThat(agent.introspect().getCapabilities()).isNotNull();
    }

    @Property
    void mockAgentWithFunctionResponderEchoesContent(
            @ForAll @StringLength(min = 1, max = 50) String content) throws Exception {
        MockAgent agent = new MockAgent("echo", msg -> "ECHO:" + msg.contentString());
        Message response = agent.process(Message.of("user", content)).get();
        assertThat(response.contentString()).isEqualTo("ECHO:" + content);
    }

    @Property
    void processResultHasTimestamp(
            @ForAll @StringLength(min = 1, max = 30) String content) throws Exception {
        MockAgent agent = new MockAgent("agent", "result");
        Message response = agent.process(Message.of("user", content)).get();
        assertThat(response.getTimestamp()).isNotNull();
    }

    @Property
    void multipleCallsAccumulateInReceived(
            @ForAll @StringLength(min = 1, max = 20) String c1,
            @ForAll @StringLength(min = 1, max = 20) String c2) throws Exception {
        MockAgent agent = new MockAgent("multi", "ok");
        agent.process(Message.of("user", c1)).get();
        agent.process(Message.of("user", c2)).get();
        assertThat(agent.getReceived()).hasSize(2);
    }

    @Property
    void fixedResponseAlwaysReturnsSameContent(
            @ForAll @StringLength(min = 1, max = 80) String question) throws Exception {
        MockAgent agent = new MockAgent("consistent", "always this");
        Message r1 = agent.process(Message.of("user", question)).get();
        Message r2 = agent.process(Message.of("user", question)).get();
        assertThat(r1.contentString()).isEqualTo(r2.contentString());
    }

    @Property
    void receivedListIsDefensiveCopy(
            @ForAll @StringLength(min = 1, max = 20) String content) throws Exception {
        MockAgent agent = new MockAgent("guard", "ok");
        agent.process(Message.of("user", content)).get();
        var copy = agent.getReceived();
        assertThatThrownBy(() -> copy.add(Message.of("user", "injected")))
                .isInstanceOf(UnsupportedOperationException.class);
    }
}
