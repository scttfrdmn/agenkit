package io.agenkit.core;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Snapshot of an agent's internal state, returned by Agent#introspect().
 */
public final class IntrospectionResult {

    private final String agentName;
    private final List<String> capabilities;
    private final Map<String, Object> memory;
    private final Map<String, Object> state;
    private final List<String> tools;

    public IntrospectionResult(
            String agentName,
            List<String> capabilities,
            Map<String, Object> memory,
            Map<String, Object> state,
            List<String> tools) {
        this.agentName = agentName;
        this.capabilities = capabilities != null
                ? Collections.unmodifiableList(capabilities)
                : Collections.emptyList();
        this.memory = memory != null
                ? Collections.unmodifiableMap(memory)
                : Collections.emptyMap();
        this.state = state != null
                ? Collections.unmodifiableMap(state)
                : Collections.emptyMap();
        this.tools = tools != null
                ? Collections.unmodifiableList(tools)
                : Collections.emptyList();
    }

    public String getAgentName() { return agentName; }
    public List<String> getCapabilities() { return capabilities; }
    public Map<String, Object> getMemory() { return memory; }
    public Map<String, Object> getState() { return state; }
    public List<String> getTools() { return tools; }

    @Override
    public String toString() {
        return "IntrospectionResult{agentName='" + agentName
                + "', capabilities=" + capabilities
                + ", tools=" + tools + "}";
    }
}
