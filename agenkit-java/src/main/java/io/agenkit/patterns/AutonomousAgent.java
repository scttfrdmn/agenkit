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
 * A goal-driven autonomous agent that continues until a goal is achieved or max iterations reached.
 */
public final class AutonomousAgent implements Agent {

    private final String name;
    private final LlmClient llmClient;
    private final int maxIterations;
    private final String completionSignal;

    public AutonomousAgent(String name, LlmClient llmClient, int maxIterations, String completionSignal) {
        this.name = name;
        this.llmClient = llmClient;
        this.maxIterations = maxIterations;
        this.completionSignal = completionSignal;
    }

    public AutonomousAgent(String name, LlmClient llmClient) {
        this(name, llmClient, 10, "TASK_COMPLETE");
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("autonomous", "goal_driven");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        return iterate(message.contentString(), new ArrayList<>(), 0);
    }

    private CompletableFuture<Message> iterate(String goal, List<String> progress, int iteration) {
        if (iteration >= maxIterations) {
            return CompletableFuture.completedFuture(
                    Message.of("assistant", "Goal pursuit ended after " + iteration + " iterations.\n"
                            + String.join("\n", progress))
                            .withMetadata("completed", false)
                            .withMetadata("iterations", iteration));
        }

        String context = progress.isEmpty()
                ? "Goal: " + goal
                : "Goal: " + goal + "\nProgress so far:\n" + String.join("\n", progress);

        return llmClient.complete(List.of(
                Message.of("system", "You are an autonomous agent. Work toward the goal step by step. "
                        + "When complete, include '" + completionSignal + "' in your response."),
                Message.of("user", context)))
                .thenCompose(response -> {
                    String text = response.contentString();
                    List<String> newProgress = new ArrayList<>(progress);
                    newProgress.add("Step " + (iteration + 1) + ": " + text);

                    if (text.contains(completionSignal)) {
                        return CompletableFuture.completedFuture(
                                Message.of("assistant", text)
                                        .withMetadata("completed", true)
                                        .withMetadata("iterations", iteration + 1));
                    }
                    return iterate(goal, newProgress, iteration + 1);
                });
    }

    @Override
    public IntrospectionResult introspect() {
        Map<String, Object> state = new HashMap<>();
        state.put("maxIterations", maxIterations);
        state.put("completionSignal", completionSignal);
        return new IntrospectionResult(name, getCapabilities(), null, state, null);
    }
}
