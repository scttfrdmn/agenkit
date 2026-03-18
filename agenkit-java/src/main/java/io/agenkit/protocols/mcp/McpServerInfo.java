package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Identity information about a connected MCP server. */
public record McpServerInfo(
        @JsonProperty("name") String name,
        @JsonProperty("version") String version) {

    /** Returns an empty server-info placeholder (name and version are empty strings). */
    public static McpServerInfo empty() {
        return new McpServerInfo("", "");
    }
}
