package io.agenkit.core;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Interface for tools that agents can invoke.
 */
public interface Tool {

    /** Unique name for this tool. */
    String getName();

    /** Human-readable description of what this tool does. */
    String getDescription();

    /**
     * Execute this tool with the given parameters.
     *
     * @param parameters key-value parameters for execution
     * @return a CompletableFuture that completes with the tool result
     */
    CompletableFuture<ToolResult> execute(Map<String, Object> parameters);
}
