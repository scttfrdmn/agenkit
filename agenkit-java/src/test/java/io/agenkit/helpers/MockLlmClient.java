package io.agenkit.helpers;

import io.agenkit.adapters.LlmClient;
import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.Function;

/**
 * A configurable mock LLM client for testing.
 */
public final class MockLlmClient implements LlmClient {

    private final String model;
    private final Function<List<Message>, String> responder;
    private final List<List<Message>> callHistory = new ArrayList<>();

    public MockLlmClient(String model, Function<List<Message>, String> responder) {
        this.model = model;
        this.responder = responder;
    }

    public MockLlmClient(Function<List<Message>, String> responder) {
        this("mock-model", responder);
    }

    public MockLlmClient(String response) {
        this("mock-model", messages -> response);
    }

    public MockLlmClient() {
        this("mock-model", messages -> {
            if (messages.isEmpty()) return "empty conversation";
            Message last = messages.get(messages.size() - 1);
            return "Response to: " + last.contentString();
        });
    }

    @Override
    public CompletableFuture<Message> complete(List<Message> messages) {
        callHistory.add(new ArrayList<>(messages));
        String response = responder.apply(messages);
        return CompletableFuture.completedFuture(Message.of("assistant", response));
    }

    @Override
    public String getModel() { return model; }

    public List<List<Message>> getCallHistory() { return List.copyOf(callHistory); }

    public int getCallCount() { return callHistory.size(); }
}
