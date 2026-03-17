package io.agenkit.helpers;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.Function;

/**
 * A configurable mock agent for testing.
 */
public final class MockAgent implements Agent {

    private final String name;
    private final List<String> capabilities;
    private final Function<Message, String> responder;
    private final List<Message> received = new ArrayList<>();

    public MockAgent(String name, Function<Message, String> responder) {
        this.name = name;
        this.capabilities = List.of("mock");
        this.responder = responder;
    }

    public MockAgent(String name, String response) {
        this(name, msg -> response);
    }

    public MockAgent(String response) {
        this("mock-agent", response);
    }

    public MockAgent() {
        this("mock-agent", msg -> "mock response to: " + msg.contentString());
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() { return capabilities; }

    @Override
    public CompletableFuture<Message> process(Message message) {
        received.add(message);
        String response = responder.apply(message);
        return CompletableFuture.completedFuture(Message.of("assistant", response));
    }

    @Override
    public IntrospectionResult introspect() {
        return new IntrospectionResult(name, capabilities, null, null, null);
    }

    public List<Message> getReceived() { return List.copyOf(received); }
}
