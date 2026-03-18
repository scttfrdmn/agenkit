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

    @Test
    void getCapabilitiesIncludesConversation() {
        ConversationalAgent agent = new ConversationalAgent("conv", new MockLlmClient());
        assertThat(agent.getCapabilities()).contains("conversation");
    }

    @Test
    void processWithSystemPrompt() throws Exception {
        MockLlmClient llm = new MockLlmClient("system-aware response");
        ConversationalAgent agent = new ConversationalAgent("test", llm,
                "You are a helpful assistant", 100);

        Message response = agent.process(Message.of("user", "hi")).get();

        assertThat(response.getRole()).isEqualTo("assistant");
        assertThat(response.contentString()).isEqualTo("system-aware response");
    }

    @Test
    void multipleSessionsIndependent() throws Exception {
        MockLlmClient llm = new MockLlmClient("response");
        ConversationalAgent agent1 = new ConversationalAgent("agent1", llm);
        ConversationalAgent agent2 = new ConversationalAgent("agent2", llm);

        agent1.process(Message.of("user", "msg1")).get();
        agent1.process(Message.of("user", "msg2")).get();

        assertThat(agent1.getHistory()).hasSize(4);
        assertThat(agent2.getHistory()).isEmpty();
    }

    @Test
    void multipleCallsWork() throws Exception {
        MockLlmClient llm = new MockLlmClient("ok");
        ConversationalAgent agent = new ConversationalAgent("test", llm);

        Message first = agent.process(Message.of("user", "hello")).get();
        Message second = agent.process(Message.of("user", "world")).get();

        assertThat(first.getRole()).isEqualTo("assistant");
        assertThat(second.getRole()).isEqualTo("assistant");
    }
}
