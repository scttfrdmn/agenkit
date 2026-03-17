package io.agenkit.patterns;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * An agent that tries a list of agents in order, falling back on failure.
 */
public final class FallbackAgent implements Agent {

    private final String name;
    private final List<Agent> chain;

    public FallbackAgent(String name, List<Agent> chain) {
        this.name = name;
        this.chain = List.copyOf(chain);
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("fallback", "resilience");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        return tryNext(message, 0, new ArrayList<>());
    }

    private CompletableFuture<Message> tryNext(Message message, int index, List<String> errors) {
        if (index >= chain.size()) {
            String allErrors = String.join("; ", errors);
            return CompletableFuture.completedFuture(
                    Message.of("assistant", "All agents failed: " + allErrors)
                            .withMetadata("fallback_exhausted", true)
                            .withMetadata("errors", errors.size()));
        }

        Agent agent = chain.get(index);
        return agent.process(message)
                .thenApply(response -> response.withMetadata("used_agent", agent.getName()))
                .exceptionallyCompose(ex -> {
                    errors.add(agent.getName() + ": " + ex.getMessage());
                    return tryNext(message, index + 1, errors);
                });
    }

    @Override
    public IntrospectionResult introspect() {
        List<String> agentNames = chain.stream().map(Agent::getName).toList();
        Map<String, Object> state = new HashMap<>();
        state.put("chainLength", chain.size());
        return new IntrospectionResult(name, getCapabilities(), null, state, agentNames);
    }
}
