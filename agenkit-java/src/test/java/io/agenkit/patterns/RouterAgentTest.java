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

    @Test
    void processReturnsAssistantRole() throws Exception {
        MockAgent defaultAgent = new MockAgent("default", "answer");
        MockLlmClient llm = new MockLlmClient("default");

        RouterAgent router = new RouterAgent("router", llm,
                Map.of("default", defaultAgent), defaultAgent);
        Message response = router.process(Message.of("user", "anything")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void getNameReturnsName() {
        MockAgent defaultAgent = new MockAgent("default");
        RouterAgent router = new RouterAgent("my-router", new MockLlmClient(),
                Map.of(), defaultAgent);
        assertThat(router.getName()).isEqualTo("my-router");
    }

    @Test
    void getCapabilitiesIncludesRouting() {
        MockAgent defaultAgent = new MockAgent("default");
        RouterAgent router = new RouterAgent("router", new MockLlmClient(),
                Map.of(), defaultAgent);
        assertThat(router.getCapabilities()).contains("routing");
    }

    @Test
    void introspectReturnsAgentName() {
        MockAgent defaultAgent = new MockAgent("default");
        RouterAgent router = new RouterAgent("router-x", new MockLlmClient(),
                Map.of(), defaultAgent);
        var result = router.introspect();
        assertThat(result.getAgentName()).isEqualTo("router-x");
    }

    @Test
    void introspectReportsRouteCount() {
        MockAgent math = new MockAgent("math");
        MockAgent science = new MockAgent("science");
        RouterAgent router = new RouterAgent("router", new MockLlmClient(),
                Map.of("math", math, "science", science), math);

        var result = router.introspect();
        assertThat(result.getState()).containsKey("routes");
    }

    @Test
    void routeMetadataAlwaysPresent() throws Exception {
        MockAgent defaultAgent = new MockAgent("default", "ok");
        MockLlmClient llm = new MockLlmClient("no-match");

        RouterAgent router = new RouterAgent("router", llm, Map.of(), defaultAgent);
        Message response = router.process(Message.of("user", "test")).get();

        assertThat(response.getMetadata()).containsKey("route");
    }

    @Test
    void defaultAgentNameInCapabilities() throws Exception {
        MockAgent defaultAgent = new MockAgent("my-default", "result");
        MockLlmClient llm = new MockLlmClient("my-default");

        RouterAgent router = new RouterAgent("router", llm,
                Map.of("my-default", defaultAgent), defaultAgent);
        Message response = router.process(Message.of("user", "go")).get();

        assertThat(response.contentString()).isEqualTo("result");
    }
}
