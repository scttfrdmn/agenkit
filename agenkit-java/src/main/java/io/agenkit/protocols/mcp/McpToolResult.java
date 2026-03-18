package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.stream.Collectors;

/** The result returned by an MCP tool call. */
public record McpToolResult(
        @JsonProperty("content") List<McpContent> content,
        @JsonProperty("isError") boolean isError) {

    /**
     * Concatenates all text-typed content blocks into a single string,
     * separated by spaces.
     */
    public static String textContent(List<McpContent> contents) {
        return contents.stream()
                .filter(c -> "text".equals(c.type()) && c.text() != null)
                .map(McpContent::text)
                .collect(Collectors.joining(" "));
    }
}
