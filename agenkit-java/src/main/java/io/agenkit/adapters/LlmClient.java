package io.agenkit.adapters;

import io.agenkit.core.Message;

import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * Interface for LLM provider clients.
 */
public interface LlmClient {

    /**
     * Send a list of messages to the LLM and return its response.
     *
     * @param messages conversation history (system + user + assistant turns)
     * @return a CompletableFuture that completes with the model's response message
     */
    CompletableFuture<Message> complete(List<Message> messages);

    /** Returns the model identifier used by this client. */
    String getModel();
}
