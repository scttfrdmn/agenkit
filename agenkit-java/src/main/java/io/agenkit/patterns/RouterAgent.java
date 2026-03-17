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
 * An agent that classifies and routes messages to specialized sub-agents.
 */
public final class RouterAgent implements Agent {

    private final String name;
    private final LlmClient llmClient;
    private final Map<String, Agent> routes;
    private final Agent defaultAgent;

    public RouterAgent(String name, LlmClient llmClient, Map<String, Agent> routes, Agent defaultAgent) {
        this.name = name;
        this.llmClient = llmClient;
        this.routes = Map.copyOf(routes);
        this.defaultAgent = defaultAgent;
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("routing", "classification");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        String routeNames = String.join(", ", routes.keySet());
        List<Message> classifyMessages = List.of(
                Message.of("system", "Classify the message into one of these categories: "
                        + routeNames + ". Respond with only the category name."),
                message);

        return llmClient.complete(classifyMessages).thenCompose(classification -> {
            String route = classification.contentString().trim().toLowerCase();
            Agent target = routes.getOrDefault(route, defaultAgent);
            if (target == null) {
                return CompletableFuture.completedFuture(
                        Message.of("assistant", "No route found for: " + route));
            }
            return target.process(message)
                    .thenApply(response -> response.withMetadata("route", route));
        });
    }

    @Override
    public IntrospectionResult introspect() {
        Map<String, Object> state = new HashMap<>();
        state.put("routes", List.copyOf(routes.keySet()));
        state.put("hasDefault", defaultAgent != null);
        return new IntrospectionResult(name, getCapabilities(), null, state, null);
    }
}
