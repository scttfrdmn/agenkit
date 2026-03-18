package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.annotation.JsonProperty;

/** A content block in an MCP tool result. */
public record McpContent(
        @JsonProperty("type") String type,
        @JsonProperty("text") String text) {}
