package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReentrantLock;

/**
 * MCP client that communicates with a server over HTTP using JSON-RPC 2.0.
 *
 * <p>Named {@code McpHttpClient} to avoid a name clash with {@link java.net.http.HttpClient}.
 */
public class McpHttpClient implements McpClient {

    private final String baseUrl;
    private final java.net.http.HttpClient http;
    private final AtomicLong nextId = new AtomicLong(0);
    private final ReentrantLock lock = new ReentrantLock();
    private final ObjectMapper mapper = new ObjectMapper();

    private McpServerInfo serverInfo = McpServerInfo.empty();

    public McpHttpClient(String baseUrl) {
        this.baseUrl = baseUrl.replaceAll("/$", "");
        this.http = java.net.http.HttpClient.newHttpClient();
    }

    @Override
    public void initialize() throws Exception {
        ObjectNode clientInfo = mapper.createObjectNode()
                .put("name", McpConstants.CLIENT_NAME)
                .put("version", McpConstants.CLIENT_VERSION);

        ObjectNode params = mapper.createObjectNode()
                .put("protocolVersion", McpConstants.PROTOCOL_VERSION);
        params.set("capabilities", mapper.createObjectNode());
        params.set("clientInfo", clientInfo);

        JsonRpcResponse resp = sendRequest("initialize", params);
        if (resp.error() != null) {
            throw new RuntimeException("mcp initialize error: " + resp.error().message());
        }
        serverInfo = McpVersionNegotiation.parseServerInfo(resp.result());
    }

    @Override
    public List<McpTool> listTools() throws Exception {
        JsonRpcResponse resp = sendRequest("tools/list", mapper.createObjectNode());
        if (resp.error() != null) {
            throw new RuntimeException("mcp tools/list error: " + resp.error().message());
        }
        List<McpTool> tools = new ArrayList<>();
        JsonNode toolsNode = resp.result().path("tools");
        if (toolsNode.isArray()) {
            for (JsonNode t : toolsNode) {
                tools.add(mapper.treeToValue(t, McpTool.class));
            }
        }
        return tools;
    }

    @Override
    public McpToolResult callTool(String name, Map<String, Object> args) throws Exception {
        ObjectNode params = mapper.createObjectNode().put("name", name);
        params.set("arguments", mapper.valueToTree(args));
        JsonRpcResponse resp = sendRequest("tools/call", params);
        if (resp.error() != null) {
            throw new RuntimeException("mcp tools/call error: " + resp.error().message());
        }
        return mapper.treeToValue(resp.result(), McpToolResult.class);
    }

    @Override
    public McpServerInfo serverInfo() {
        return serverInfo;
    }

    @Override
    public void close() {
        // java.net.http.HttpClient is not closeable in Java 17; nothing to release.
    }

    // -------------------------------------------------------------------------

    private JsonRpcResponse sendRequest(String method, JsonNode params) throws Exception {
        lock.lock();
        try {
            long id = nextId.incrementAndGet();
            JsonRpcRequest req = JsonRpcRequest.of(id, method, params);
            String body = mapper.writeValueAsString(req);
            HttpRequest httpReq = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl))
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .header("Content-Type", "application/json")
                    .build();
            HttpResponse<String> resp = http.send(httpReq, HttpResponse.BodyHandlers.ofString());
            return mapper.readValue(resp.body(), JsonRpcResponse.class);
        } finally {
            lock.unlock();
        }
    }
}
