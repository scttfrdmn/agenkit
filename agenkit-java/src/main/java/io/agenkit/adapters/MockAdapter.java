package io.agenkit.adapters;

import io.agenkit.core.Message;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.Function;

/**
 * Mock LLM client for testing. Returns a configurable response.
 */
public final class MockAdapter implements LlmClient {

    private final String model;
    private final Function<List<Message>, String> responder;

    public MockAdapter(String model, Function<List<Message>, String> responder) {
        this.model = model;
        this.responder = responder;
    }

    public MockAdapter(String response) {
        this("mock-model", messages -> response);
    }

    public MockAdapter() {
        this("mock-model", messages -> {
            Message last = messages.isEmpty() ? null : messages.get(messages.size() - 1);
            String input = last != null ? last.contentString() : "";
            return "Mock response to: " + input;
        });
    }

    @Override
    public CompletableFuture<Message> complete(List<Message> messages) {
        String response = responder.apply(messages);
        return CompletableFuture.completedFuture(Message.of("assistant", response));
    }

    @Override
    public String getModel() { return model; }
}
