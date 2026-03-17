package io.agenkit.composition;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Composes agents into a sequential pipeline.
 * The output of each agent becomes the input to the next.
 */
public final class SequentialAgent implements Agent {

    private final String name;
    private final List<Agent> pipeline;

    public SequentialAgent(String name, List<Agent> pipeline) {
        this.name = name;
        this.pipeline = List.copyOf(pipeline);
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("sequential_composition", "pipeline");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        CompletableFuture<Message> chain = CompletableFuture.completedFuture(message);
        for (Agent agent : pipeline) {
            chain = chain.thenCompose(agent::process);
        }
        return chain.thenApply(result ->
                result.withMetadata("pipeline_length", pipeline.size()));
    }

    @Override
    public IntrospectionResult introspect() {
        List<String> agentNames = pipeline.stream().map(Agent::getName).toList();
        Map<String, Object> state = new HashMap<>();
        state.put("pipelineLength", pipeline.size());
        return new IntrospectionResult(name, getCapabilities(), null, state, agentNames);
    }
}
