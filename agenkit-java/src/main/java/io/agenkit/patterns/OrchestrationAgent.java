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
 * An agent that orchestrates others in sequential, parallel, or router modes.
 */
public final class OrchestrationAgent implements Agent {

    public enum Mode { SEQUENTIAL, PARALLEL, ROUTER }

    private final String name;
    private final List<Agent> agents;
    private final Mode mode;

    public OrchestrationAgent(String name, List<Agent> agents, Mode mode) {
        this.name = name;
        this.agents = List.copyOf(agents);
        this.mode = mode;
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("orchestration", mode.name().toLowerCase());
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        return switch (mode) {
            case SEQUENTIAL -> processSequential(message);
            case PARALLEL -> processParallel(message);
            case ROUTER -> processRouter(message);
        };
    }

    private CompletableFuture<Message> processSequential(Message message) {
        CompletableFuture<Message> chain = CompletableFuture.completedFuture(message);
        for (Agent agent : agents) {
            chain = chain.thenCompose(agent::process);
        }
        return chain;
    }

    private CompletableFuture<Message> processParallel(Message message) {
        List<CompletableFuture<Message>> futures = agents.stream()
                .map(a -> a.process(message))
                .toList();
        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenApply(v -> {
                    List<String> results = futures.stream()
                            .map(f -> f.join().contentString())
                            .toList();
                    return Message.of("assistant", String.join("\n---\n", results))
                            .withMetadata("mode", "parallel")
                            .withMetadata("agent_count", agents.size());
                });
    }

    private CompletableFuture<Message> processRouter(Message message) {
        // Route to first agent whose name appears in the message
        String content = message.contentString().toLowerCase();
        for (Agent agent : agents) {
            if (content.contains(agent.getName().toLowerCase())) {
                return agent.process(message)
                        .thenApply(r -> r.withMetadata("routed_to", agent.getName()));
            }
        }
        // Default: first agent
        if (!agents.isEmpty()) {
            return agents.get(0).process(message)
                    .thenApply(r -> r.withMetadata("routed_to", agents.get(0).getName()));
        }
        return CompletableFuture.completedFuture(Message.of("assistant", "No agents available"));
    }

    @Override
    public IntrospectionResult introspect() {
        List<String> agentNames = agents.stream().map(Agent::getName).toList();
        Map<String, Object> state = new HashMap<>();
        state.put("mode", mode.name());
        state.put("agentCount", agents.size());
        return new IntrospectionResult(name, getCapabilities(), null, state, agentNames);
    }
}
