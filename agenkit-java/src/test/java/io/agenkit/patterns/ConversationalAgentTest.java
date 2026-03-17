package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockLlmClient;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class ConversationalAgentTest {

    @Test
    void processReturnsResponse() throws Exception {
        MockLlmClient llm = new MockLlmClient("Hello back!");
        ConversationalAgent agent = new ConversationalAgent("test", llm);

        Message response = agent.process(Message.of("user", "Hello")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
        assertThat(response.contentString()).isEqualTo("Hello back!");
    }

    @Test
    void historyAccumulates() throws Exception {
        MockLlmClient llm = new MockLlmClient("response");
        ConversationalAgent agent = new ConversationalAgent("test", llm);

        agent.process(Message.of("user", "first")).get();
        agent.process(Message.of("user", "second")).get();

        assertThat(agent.getHistory()).hasSize(4); // 2 user + 2 assistant
    }

    @Test
    void clearHistoryWorks() throws Exception {
        MockLlmClient llm = new MockLlmClient("response");
        ConversationalAgent agent = new ConversationalAgent("test", llm);

        agent.process(Message.of("user", "hello")).get();
        agent.clearHistory(false);

        assertThat(agent.getHistory()).isEmpty();
    }

    @Test
    void getNameReturnsName() {
        ConversationalAgent agent = new ConversationalAgent("my-agent",
                new MockLlmClient());
        assertThat(agent.getName()).isEqualTo("my-agent");
    }

    @Test
    void introspectReturnsState() throws Exception {
        MockLlmClient llm = new MockLlmClient("hi");
        ConversationalAgent agent = new ConversationalAgent("test", llm);
        agent.process(Message.of("user", "hello")).get();

        var result = agent.introspect();
        assertThat(result.getAgentName()).isEqualTo("test");
        assertThat(result.getState()).containsKey("historySize");
    }
}
