package io.agenkit.patterns;

import io.agenkit.adapters.LlmClient;
import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * An agent that generates a response, critiques it, and refines based on feedback.
 */
public final class ReflectionAgent implements Agent {

    private final String name;
    private final LlmClient llmClient;
    private final int maxIterations;

    public ReflectionAgent(String name, LlmClient llmClient, int maxIterations) {
        this.name = name;
        this.llmClient = llmClient;
        this.maxIterations = maxIterations;
    }

    public ReflectionAgent(String name, LlmClient llmClient) {
        this(name, llmClient, 2);
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("reflection", "self_critique", "refinement");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        return generateInitial(message).thenCompose(initial ->
                refine(message, initial.contentString(), 0));
    }

    private CompletableFuture<Message> generateInitial(Message message) {
        return llmClient.complete(List.of(
                Message.of("system", "You are a helpful assistant. Provide a thorough response."),
                message));
    }

    private CompletableFuture<Message> refine(Message original, String current, int iteration) {
        if (iteration >= maxIterations) {
            return CompletableFuture.completedFuture(
                    Message.of("assistant", current)
                            .withMetadata("iterations", iteration)
                            .withMetadata("refined", iteration > 0));
        }

        return llmClient.complete(List.of(
                Message.of("system", "Critique this response and identify specific improvements."),
                Message.of("user", "Original question: " + original.contentString()
                        + "\n\nResponse to critique:\n" + current)))
                .thenCompose(critique ->
                        llmClient.complete(List.of(
                                Message.of("system", "Improve your response based on the critique."),
                                Message.of("user", "Original question: " + original.contentString()),
                                Message.of("assistant", current),
                                Message.of("user", "Critique: " + critique.contentString()
                                        + "\n\nPlease provide an improved response.")))
                                .thenCompose(improved ->
                                        refine(original, improved.contentString(), iteration + 1)));
    }

    @Override
    public IntrospectionResult introspect() {
        Map<String, Object> state = new HashMap<>();
        state.put("maxIterations", maxIterations);
        return new IntrospectionResult(name, getCapabilities(), null, state, null);
    }
}
