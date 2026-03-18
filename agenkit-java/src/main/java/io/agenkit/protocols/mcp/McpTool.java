package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Describes a tool exposed by an MCP server. */
public record McpTool(
        @JsonProperty("name") String name,
        @JsonProperty("description") String description) {}
