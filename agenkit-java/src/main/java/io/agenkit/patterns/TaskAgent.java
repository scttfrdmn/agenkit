package io.agenkit.patterns;

import io.agenkit.adapters.LlmClient;
import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicReference;

/**
 * A one-shot task agent with explicit lifecycle management.
 */
public final class TaskAgent implements Agent {

    public enum Status { IDLE, RUNNING, COMPLETE, FAILED }

    private final String name;
    private final LlmClient llmClient;
    private final String taskDescription;
    private final AtomicReference<Status> status = new AtomicReference<>(Status.IDLE);
    private volatile Message lastResult;

    public TaskAgent(String name, LlmClient llmClient, String taskDescription) {
        this.name = name;
        this.llmClient = llmClient;
        this.taskDescription = taskDescription;
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("task_execution", "lifecycle_management");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        if (!status.compareAndSet(Status.IDLE, Status.RUNNING)) {
            return CompletableFuture.completedFuture(
                    Message.of("assistant", "Task agent is not idle. Status: " + status.get()));
        }

        return llmClient.complete(List.of(
                Message.of("system", "Task: " + taskDescription + "\nComplete this specific task."),
                message))
                .thenApply(response -> {
                    status.set(Status.COMPLETE);
                    lastResult = response;
                    return response.withMetadata("task_status", "complete")
                            .withMetadata("task", taskDescription);
                })
                .exceptionally(ex -> {
                    status.set(Status.FAILED);
                    Message err = Message.of("assistant", "Task failed: " + ex.getMessage())
                            .withMetadata("task_status", "failed");
                    lastResult = err;
                    return err;
                });
    }

    public void reset() { status.set(Status.IDLE); }

    public Status getStatus() { return status.get(); }

    public Message getLastResult() { return lastResult; }

    @Override
    public IntrospectionResult introspect() {
        Map<String, Object> state = new HashMap<>();
        state.put("status", status.get().name());
        state.put("task", taskDescription);
        return new IntrospectionResult(name, getCapabilities(), null, state, null);
    }
}
