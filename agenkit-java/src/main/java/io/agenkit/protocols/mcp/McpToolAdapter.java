package io.agenkit.protocols.mcp;

import io.agenkit.core.Tool;
import io.agenkit.core.ToolResult;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Wraps an {@link McpTool} descriptor and an {@link McpClient} as an {@link Tool},
 * bridging the MCP protocol into the agenkit tool abstraction.
 *
 * <p>Package-private: callers should use {@link McpTools#fromClient(McpClient)}.
 */
class McpToolAdapter implements Tool {

    private final McpClient client;
    private final McpTool mcpTool;

    McpToolAdapter(McpClient client, McpTool mcpTool) {
        this.client = client;
        this.mcpTool = mcpTool;
    }

    @Override
    public String getName() {
        return mcpTool.name();
    }

    @Override
    public String getDescription() {
        return mcpTool.description();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> parameters) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                McpToolResult result = client.callTool(getName(), parameters);
                String text = McpToolResult.textContent(result.content());
                if (result.isError()) {
                    return ToolResult.fail(text);
                }
                return ToolResult.ok(text);
            } catch (Exception e) {
                return ToolResult.fail(e.getMessage());
            }
        });
    }
}
