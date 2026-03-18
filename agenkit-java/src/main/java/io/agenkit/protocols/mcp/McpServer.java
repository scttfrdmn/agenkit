package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.agenkit.core.Tool;
import io.agenkit.core.ToolResult;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * An MCP server that exposes a list of {@link Tool} instances over a stdio transport.
 *
 * <p>The server reads JSON-RPC requests from stdin, one per line, dispatches them to
 * the registered tools, and writes JSON-RPC responses to stdout.
 */
public class McpServer {

    private final String name;
    private final String version;
    private final Map<String, Tool> tools;
    private final ObjectMapper mapper = new ObjectMapper();

    public McpServer(String name, String version, List<Tool> tools) {
        this.name = name;
        this.version = version;
        this.tools = tools.stream()
                .collect(Collectors.toMap(Tool::getName, t -> t));
    }

    /**
     * Blocks and serves requests from {@link System#in} until EOF.
     *
     * @throws IOException if an I/O error occurs reading or writing
     */
    public void serveStdio() throws IOException {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        PrintWriter out = new PrintWriter(new OutputStreamWriter(System.out), true);
        String line;
        while ((line = in.readLine()) != null) {
            String response;
            try {
                JsonRpcRequest req = mapper.readValue(line, JsonRpcRequest.class);
                JsonRpcResponse resp = handleRequest(req);
                response = mapper.writeValueAsString(resp);
            } catch (Exception e) {
                response = "{\"jsonrpc\":\"2.0\",\"id\":0,\"error\":{\"code\":-32700,\"message\":\"parse error\"}}";
            }
            out.println(response);
        }
    }

    /**
     * Handles a single JSON-RPC request and returns the response.
     *
     * <p>This method is intentionally public so that tests can drive the server
     * without needing actual stdio.
     */
    public JsonRpcResponse handleRequest(JsonRpcRequest req) {
        return switch (req.method()) {
            case "initialize" -> handleInitialize(req);
            case "tools/list" -> handleToolsList(req);
            case "tools/call" -> handleToolsCall(req);
            default -> errorResponse(req.id(), -32601, "method not found: " + req.method());
        };
    }

    // -------------------------------------------------------------------------
    // Private helpers
    // -------------------------------------------------------------------------

    private JsonRpcResponse handleInitialize(JsonRpcRequest req) {
        ObjectNode result = mapper.createObjectNode()
                .put("protocolVersion", McpConstants.PROTOCOL_VERSION);
        result.set("capabilities", mapper.createObjectNode());
        ObjectNode serverInfo = mapper.createObjectNode()
                .put("name", name)
                .put("version", version);
        result.set("serverInfo", serverInfo);
        return okResponse(req.id(), result);
    }

    private JsonRpcResponse handleToolsList(JsonRpcRequest req) {
        ArrayNode toolsArray = mapper.createArrayNode();
        for (Tool tool : tools.values()) {
            toolsArray.add(mapper.createObjectNode()
                    .put("name", tool.getName())
                    .put("description", tool.getDescription()));
        }
        ObjectNode result = mapper.createObjectNode();
        result.set("tools", toolsArray);
        return okResponse(req.id(), result);
    }

    private JsonRpcResponse handleToolsCall(JsonRpcRequest req) {
        JsonNode params = req.params();
        if (params == null || !params.has("name")) {
            return errorResponse(req.id(), -32602, "missing parameter: name");
        }
        String toolName = params.get("name").asText();
        Tool tool = tools.get(toolName);
        if (tool == null) {
            return errorResponse(req.id(), -32602, "tool not found: " + toolName);
        }

        Map<String, Object> args = new HashMap<>();
        JsonNode argsNode = params.path("arguments");
        if (argsNode.isObject()) {
            argsNode.fields().forEachRemaining(e -> args.put(e.getKey(), e.getValue().asText()));
        }

        try {
            ToolResult toolResult = tool.execute(args).get();
            ArrayNode content = mapper.createArrayNode();
            String text = toolResult.isSuccess()
                    ? String.valueOf(toolResult.getData())
                    : toolResult.getError();
            content.add(mapper.createObjectNode()
                    .put("type", "text")
                    .put("text", text));
            ObjectNode result = mapper.createObjectNode()
                    .put("isError", !toolResult.isSuccess());
            result.set("content", content);
            return okResponse(req.id(), result);
        } catch (Exception e) {
            return errorResponse(req.id(), -32603, "tool execution error: " + e.getMessage());
        }
    }

    private JsonRpcResponse okResponse(long id, JsonNode result) {
        return new JsonRpcResponse("2.0", id, result, null);
    }

    private JsonRpcResponse errorResponse(long id, int code, String message) {
        return new JsonRpcResponse("2.0", id, null, new JsonRpcError(code, message));
    }
}
