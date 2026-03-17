package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import io.agenkit.helpers.MockLlmClient;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class CollaborativeAgentTest {

    @Test
    void synthesizesPeerResponses() throws Exception {
        MockAgent peer1 = new MockAgent("peer1", "opinion A");
        MockAgent peer2 = new MockAgent("peer2", "opinion B");
        MockLlmClient llm = new MockLlmClient("consensus: both A and B are valid");

        CollaborativeAgent agent = new CollaborativeAgent("collab", llm,
                List.of(peer1, peer2));

        Message response = agent.process(Message.of("user", "what is the answer?")).get();

        assertThat(response.contentString()).contains("consensus");
        assertThat(response.getMetadata()).containsEntry("peer_count", 2);
    }

    @Test
    void getCapabilitiesIncludesConsensus() {
        CollaborativeAgent agent = new CollaborativeAgent("collab", new MockLlmClient(),
                List.of(new MockAgent()));
        assertThat(agent.getCapabilities()).contains("consensus");
    }

    @Test
    void introspectReportsPeerCount() {
        MockAgent p1 = new MockAgent("p1");
        MockAgent p2 = new MockAgent("p2");
        CollaborativeAgent agent = new CollaborativeAgent("collab", new MockLlmClient(),
                List.of(p1, p2));

        var result = agent.introspect();
        assertThat(result.getState()).containsEntry("peerCount", 2);
    }
}
