package io.agenkit.helpers;

import io.agenkit.core.Tool;
import io.agenkit.core.ToolResult;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Function;

/**
 * A configurable mock tool for testing.
 */
public final class MockTool implements Tool {

    private final String name;
    private final String description;
    private final Function<Map<String, Object>, ToolResult> executor;
    private final List<Map<String, Object>> callHistory = new ArrayList<>();

    public MockTool(String name, String description, Function<Map<String, Object>, ToolResult> executor) {
        this.name = name;
        this.description = description;
        this.executor = executor;
    }

    public MockTool(String name, String response) {
        this(name, "mock tool", params -> ToolResult.ok(response));
    }

    public MockTool(String name) {
        this(name, "mock tool", params -> ToolResult.ok("result from " + name));
    }

    @Override
    public String getName() { return name; }

    @Override
    public String getDescription() { return description; }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> parameters) {
        callHistory.add(Map.copyOf(parameters));
        ToolResult result = executor.apply(parameters);
        return CompletableFuture.completedFuture(result);
    }

    public List<Map<String, Object>> getCallHistory() { return List.copyOf(callHistory); }

    public int getCallCount() { return callHistory.size(); }
}
