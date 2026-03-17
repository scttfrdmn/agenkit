package io.agenkit.patterns;

import io.agenkit.adapters.LlmClient;
import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Multi-agent orchestrator that coordinates multiple specialized agents.
 */
public final class MultiAgentOrchestrator implements Agent {

    private final String name;
    private final LlmClient llmClient;
    private final Map<String, Agent> agents;

    public MultiAgentOrchestrator(String name, LlmClient llmClient, Map<String, Agent> agents) {
        this.name = name;
        this.llmClient = llmClient;
        this.agents = Map.copyOf(agents);
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("multi_agent", "orchestration", "coordination");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        StringBuilder agentDesc = new StringBuilder("Available agents:\n");
        for (Map.Entry<String, Agent> entry : agents.entrySet()) {
            agentDesc.append("- ").append(entry.getKey())
                    .append(": ").append(entry.getValue().getCapabilities()).append("\n");
        }

        return llmClient.complete(List.of(
                Message.of("system", agentDesc + "\nRespond with: AGENT: agent_name\nTASK: task description"),
                message))
                .thenCompose(routing -> {
                    String routingText = routing.contentString();
                    String agentName = null;
                    String task = message.contentString();

                    for (String line : routingText.split("\n")) {
                        if (line.startsWith("AGENT:")) {
                            agentName = line.substring("AGENT:".length()).trim();
                        } else if (line.startsWith("TASK:")) {
                            task = line.substring("TASK:".length()).trim();
                        }
                    }

                    Agent target = agentName != null ? agents.get(agentName) : null;
                    if (target == null && !agents.isEmpty()) {
                        target = agents.values().iterator().next();
                    }
                    if (target == null) {
                        return CompletableFuture.completedFuture(
                                Message.of("assistant", "No agents available"));
                    }

                    final String finalTask = task;
                    final String finalAgentName = agentName;
                    return target.process(Message.of("user", finalTask))
                            .thenApply(r -> r.withMetadata("orchestrator", name)
                                    .withMetadata("delegated_to", finalAgentName));
                });
    }

    @Override
    public IntrospectionResult introspect() {
        List<String> agentNames = new ArrayList<>(agents.keySet());
        Map<String, Object> state = new HashMap<>();
        state.put("agentCount", agents.size());
        return new IntrospectionResult(name, getCapabilities(), null, state, agentNames);
    }
}
