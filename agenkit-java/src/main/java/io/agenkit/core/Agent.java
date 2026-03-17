package io.agenkit.core;

import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * Core interface that all agents must implement.
 */
public interface Agent {

    /** Human-readable name for this agent. */
    String getName();

    /** Capabilities this agent advertises. */
    List<String> getCapabilities();

    /**
     * Process a message asynchronously and return the agent's response.
     *
     * @param message the incoming message
     * @return a CompletableFuture that completes with the agent's response
     */
    CompletableFuture<Message> process(Message message);

    /** Returns a snapshot of this agent's current state. */
    IntrospectionResult introspect();
}
