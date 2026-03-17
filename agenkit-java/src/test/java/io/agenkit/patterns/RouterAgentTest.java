package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import io.agenkit.helpers.MockLlmClient;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.*;

class RouterAgentTest {

    @Test
    void routesToCorrectAgent() throws Exception {
        MockAgent mathAgent = new MockAgent("math", "42");
        MockAgent scienceAgent = new MockAgent("science", "E=mc2");

        MockLlmClient llm = new MockLlmClient("math");
        RouterAgent router = new RouterAgent("router", llm,
                Map.of("math", mathAgent, "science", scienceAgent), mathAgent);

        Message response = router.process(Message.of("user", "What is 6x7?")).get();

        assertThat(response.contentString()).isEqualTo("42");
        assertThat(response.getMetadata()).containsEntry("route", "math");
    }

    @Test
    void usesDefaultOnUnknownRoute() throws Exception {
        MockAgent defaultAgent = new MockAgent("default", "default response");
        MockLlmClient llm = new MockLlmClient("unknown_route");

        RouterAgent router = new RouterAgent("router", llm, Map.of(), defaultAgent);
        Message response = router.process(Message.of("user", "something")).get();

        assertThat(response.contentString()).isEqualTo("default response");
    }
}
