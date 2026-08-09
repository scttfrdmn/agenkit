package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Identity information about a connected MCP server.
 *
 * @param name server name as self-reported during initialization
 * @param version server version string
 * @param protocolVersion the MCP protocol revision the server actually reported in its
 *     initialize response (the top-level {@code result.protocolVersion} field). Captured so a
 *     caller has a single place to check it after {@code initialize()} (agenkit#781 — this field
 *     did not exist before, so a peer speaking a different revision was indistinguishable from
 *     one speaking ours).
 */
public record McpServerInfo(
        @JsonProperty("name") String name,
        @JsonProperty("version") String version,
        @JsonProperty("protocolVersion") String protocolVersion) {

    /** Returns an empty server-info placeholder (all fields are empty strings). */
    public static McpServerInfo empty() {
        return new McpServerInfo("", "", "");
    }
}
