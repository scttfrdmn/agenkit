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
 * A supervisor agent that decomposes tasks and delegates to worker agents.
 */
public final class SupervisorAgent implements Agent {

    private final String name;
    private final LlmClient llmClient;
    private final List<Agent> workers;

    public SupervisorAgent(String name, LlmClient llmClient, List<Agent> workers) {
        this.name = name;
        this.llmClient = llmClient;
        this.workers = List.copyOf(workers);
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("supervision", "task_decomposition", "delegation");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        StringBuilder workerDesc = new StringBuilder("Available workers:\n");
        for (Agent worker : workers) {
            workerDesc.append("- ").append(worker.getName())
                    .append(": ").append(worker.getCapabilities()).append("\n");
        }

        List<Message> planMessages = List.of(
                Message.of("system", workerDesc + "\nDecompose the task. Format: WORKER_NAME: subtask"),
                message);

        return llmClient.complete(planMessages).thenCompose(plan -> {
            List<CompletableFuture<String>> tasks = new ArrayList<>();
            for (String line : plan.contentString().split("\n")) {
                for (Agent worker : workers) {
                    if (line.startsWith(worker.getName() + ":")) {
                        String subtask = line.substring(worker.getName().length() + 1).trim();
                        tasks.add(worker.process(Message.of("user", subtask))
                                .thenApply(r -> worker.getName() + ": " + r.contentString()));
                        break;
                    }
                }
            }

            if (tasks.isEmpty()) {
                // Fall back to first worker
                Agent first = workers.isEmpty() ? null : workers.get(0);
                if (first == null) {
                    return CompletableFuture.completedFuture(
                            Message.of("assistant", "No workers available"));
                }
                return first.process(message)
                        .thenApply(r -> r.withMetadata("supervisor", name));
            }

            return CompletableFuture.allOf(tasks.toArray(new CompletableFuture[0]))
                    .thenApply(v -> {
                        List<String> results = tasks.stream()
                                .map(CompletableFuture::join)
                                .toList();
                        return Message.of("assistant", String.join("\n", results))
                                .withMetadata("supervisor", name)
                                .withMetadata("workers_used", tasks.size());
                    });
        });
    }

    @Override
    public IntrospectionResult introspect() {
        List<String> workerNames = workers.stream().map(Agent::getName).toList();
        Map<String, Object> state = new HashMap<>();
        state.put("workerCount", workers.size());
        return new IntrospectionResult(name, getCapabilities(), null, state, workerNames);
    }
}
