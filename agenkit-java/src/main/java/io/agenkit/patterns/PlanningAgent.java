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
 * An agent that creates a plan then executes it step by step.
 */
public final class PlanningAgent implements Agent {

    private final String name;
    private final LlmClient llmClient;
    private final int maxSteps;
    private final List<String> lastPlan = new ArrayList<>();

    public PlanningAgent(String name, LlmClient llmClient, int maxSteps) {
        this.name = name;
        this.llmClient = llmClient;
        this.maxSteps = maxSteps;
    }

    public PlanningAgent(String name, LlmClient llmClient) {
        this(name, llmClient, 10);
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("planning", "step_execution");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        List<Message> planMessages = List.of(
                Message.of("system", "Create a numbered step-by-step plan to complete the task. Format: 1. step one\n2. step two\n..."),
                message);

        return llmClient.complete(planMessages).thenCompose(planResponse -> {
            List<String> steps = parsePlan(planResponse.contentString());
            lastPlan.clear();
            lastPlan.addAll(steps);

            return executePlan(message.contentString(), steps, 0, new ArrayList<>());
        });
    }

    private CompletableFuture<Message> executePlan(
            String originalTask, List<String> steps, int stepIndex, List<String> results) {
        if (stepIndex >= steps.size() || stepIndex >= maxSteps) {
            String summary = "Task: " + originalTask + "\n\nExecuted " + results.size() + " steps:\n"
                    + String.join("\n", results);
            return CompletableFuture.completedFuture(
                    Message.of("assistant", summary)
                            .withMetadata("plan_steps", steps.size())
                            .withMetadata("executed_steps", results.size()));
        }

        String step = steps.get(stepIndex);
        List<Message> executeMessages = List.of(
                Message.of("system", "Execute this specific step of the plan. Be concise."),
                Message.of("user", "Step " + (stepIndex + 1) + ": " + step));

        return llmClient.complete(executeMessages).thenCompose(result -> {
            List<String> newResults = new ArrayList<>(results);
            newResults.add("Step " + (stepIndex + 1) + " (" + step + "): " + result.contentString());
            return executePlan(originalTask, steps, stepIndex + 1, newResults);
        });
    }

    private List<String> parsePlan(String planText) {
        List<String> steps = new ArrayList<>();
        for (String line : planText.split("\n")) {
            String trimmed = line.trim();
            if (trimmed.matches("^\\d+\\..*")) {
                steps.add(trimmed.replaceFirst("^\\d+\\.\\s*", "").trim());
            }
        }
        return steps.isEmpty() ? List.of(planText) : steps;
    }

    public List<String> getLastPlan() { return List.copyOf(lastPlan); }

    @Override
    public IntrospectionResult introspect() {
        Map<String, Object> state = new HashMap<>();
        state.put("maxSteps", maxSteps);
        state.put("lastPlanSteps", lastPlan.size());
        return new IntrospectionResult(name, getCapabilities(), null, state, null);
    }
}
