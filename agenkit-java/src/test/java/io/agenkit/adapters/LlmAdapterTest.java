package io.agenkit.adapters;

import io.agenkit.core.Message;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class LlmAdapterTest {

    @Test
    void mockAdapterReturnsFixedResponse() throws Exception {
        MockAdapter adapter = new MockAdapter("hello from mock");
        Message response = adapter.complete(List.of(Message.of("user", "anything"))).get();
        assertThat(response.contentString()).isEqualTo("hello from mock");
    }

    @Test
    void mockAdapterRoleIsAssistant() throws Exception {
        MockAdapter adapter = new MockAdapter("my reply");
        Message response = adapter.complete(List.of(Message.of("user", "q"))).get();
        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void mockAdapterGetModelReturnsModelName() {
        MockAdapter adapter = new MockAdapter("mock-model", messages -> "reply");
        assertThat(adapter.getModel()).isEqualTo("mock-model");
    }

    @Test
    void mockAdapterDefaultResponderEchosInput() throws Exception {
        MockAdapter adapter = new MockAdapter();
        Message response = adapter.complete(List.of(Message.of("user", "echo this"))).get();
        assertThat(response.contentString()).contains("echo this");
    }

    @Test
    void mockAdapterWithFunctionResponder() throws Exception {
        MockAdapter adapter = new MockAdapter("test-model",
                messages -> "processed: " + messages.get(messages.size() - 1).contentString());
        Message response = adapter.complete(List.of(Message.of("user", "input-data"))).get();
        assertThat(response.contentString()).isEqualTo("processed: input-data");
    }

    @Test
    void mockAdapterHandlesMultipleMessages() throws Exception {
        MockAdapter adapter = new MockAdapter("last");
        List<Message> conversation = List.of(
                Message.of("system", "you are helpful"),
                Message.of("user", "first"),
                Message.of("assistant", "reply"),
                Message.of("user", "follow-up")
        );
        Message response = adapter.complete(conversation).get();
        assertThat(response.contentString()).isEqualTo("last");
    }

    @Test
    void mockAdapterHandlesEmptyMessageList() throws Exception {
        MockAdapter adapter = new MockAdapter();
        Message response = adapter.complete(List.of()).get();
        assertThat(response).isNotNull();
        assertThat(response.getRole()).isEqualTo("assistant");
    }

    @Test
    void llmClientInterfaceIsImplemented() {
        LlmClient client = new MockAdapter("check");
        assertThat(client).isInstanceOf(LlmClient.class);
        assertThat(client.getModel()).isNotNull();
    }

    @Test
    void mockAdapterDefaultModelIsMockModel() {
        MockAdapter adapter = new MockAdapter("response");
        assertThat(adapter.getModel()).isEqualTo("mock-model");
    }

    @Test
    void mockAdapterRespondsWithCorrectContentType() throws Exception {
        MockAdapter adapter = new MockAdapter("model-x", messages -> "structured");
        Message response = adapter.complete(List.of(Message.of("user", "test"))).get();
        assertThat(response.contentString()).isEqualTo("structured");
        assertThat(response.getTimestamp()).isNotNull();
    }
}
