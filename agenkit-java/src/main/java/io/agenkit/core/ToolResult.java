package io.agenkit.core;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Result of a tool execution.
 */
public final class ToolResult {

    private final boolean success;
    private final Object data;
    private final String error;
    private final Map<String, Object> metadata;

    public ToolResult(boolean success, Object data, String error, Map<String, Object> metadata) {
        this.success = success;
        this.data = data;
        this.error = error;
        this.metadata = metadata != null
                ? Collections.unmodifiableMap(new HashMap<>(metadata))
                : Collections.emptyMap();
    }

    /** Create a successful result with data. */
    public static ToolResult ok(Object data) {
        return new ToolResult(true, data, null, Collections.emptyMap());
    }

    /** Create a failed result with an error message. */
    public static ToolResult fail(String error) {
        return new ToolResult(false, null, error, Collections.emptyMap());
    }

    /** Returns a copy with an additional metadata entry. */
    public ToolResult withMetadata(String key, Object value) {
        Map<String, Object> newMeta = new HashMap<>(this.metadata);
        newMeta.put(key, value);
        return new ToolResult(success, data, error, newMeta);
    }

    public boolean isSuccess() { return success; }
    public Object getData() { return data; }
    public String getError() { return error; }
    public Map<String, Object> getMetadata() { return metadata; }

    @Override
    public String toString() {
        if (success) {
            return "ToolResult{success=true, data=" + data + "}";
        }
        return "ToolResult{success=false, error='" + error + "'}";
    }
}
