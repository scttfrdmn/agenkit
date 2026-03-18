package io.agenkit.protocols.mcp;

import io.agenkit.core.Tool;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Static factory that converts MCP tool descriptors into {@link Tool} instances.
 *
 * <p>Usage:
 * <pre>{@code
 * try (McpClient client = new StdioClient("npx", "-y", "@modelcontextprotocol/server-everything")) {
 *     client.initialize();
 *     List<Tool> tools = McpTools.fromClient(client);
 *     // pass tools to an Agent
 * }
 * }</pre>
 */
public final class McpTools {

    private McpTools() {}

    /**
     * Queries the client for its tool list and returns each one wrapped as a {@link Tool}.
     *
     * @param client an initialised {@link McpClient}
     * @return list of tools backed by the given client
     * @throws Exception if the {@code tools/list} RPC fails
     */
    public static List<Tool> fromClient(McpClient client) throws Exception {
        List<McpTool> mcpTools = client.listTools();
        return mcpTools.stream()
                .map(t -> (Tool) new McpToolAdapter(client, t))
                .collect(Collectors.toList());
    }
}
