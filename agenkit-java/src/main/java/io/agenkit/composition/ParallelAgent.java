package io.agenkit.composition;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Fans out to multiple agents in parallel and aggregates results.
 */
public final class ParallelAgent implements Agent {

    private final String name;
    private final List<Agent> agents;
    private final String separator;

    public ParallelAgent(String name, List<Agent> agents, String separator) {
        this.name = name;
        this.agents = List.copyOf(agents);
        this.separator = separator;
    }

    public ParallelAgent(String name, List<Agent> agents) {
        this(name, agents, "\n---\n");
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("parallel_composition", "fan_out");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        List<CompletableFuture<Message>> futures = agents.stream()
                .map(a -> a.process(message))
                .toList();

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenApply(v -> {
                    List<String> results = futures.stream()
                            .map(f -> f.join().contentString())
                            .toList();
                    return Message.of("assistant", String.join(separator, results))
                            .withMetadata("parallel_count", agents.size());
                });
    }

    @Override
    public IntrospectionResult introspect() {
        List<String> agentNames = agents.stream().map(Agent::getName).toList();
        Map<String, Object> state = new HashMap<>();
        state.put("agentCount", agents.size());
        return new IntrospectionResult(name, getCapabilities(), null, state, agentNames);
    }
}
