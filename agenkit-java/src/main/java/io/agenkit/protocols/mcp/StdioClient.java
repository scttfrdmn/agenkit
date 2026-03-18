package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReentrantLock;

/**
 * MCP client that communicates with a server subprocess over stdin/stdout.
 *
 * <p>All wire I/O is line-delimited JSON-RPC 2.0. Access is serialised with a
 * {@link ReentrantLock} so that callers from different threads are safe.
 */
public class StdioClient implements McpClient {

    private final String command;
    private final List<String> args;

    private Process process;
    private BufferedReader reader;
    private BufferedWriter writer;

    private final AtomicLong nextId = new AtomicLong(0);
    private final ReentrantLock lock = new ReentrantLock();
    private final ObjectMapper mapper = new ObjectMapper();

    private McpServerInfo serverInfo = McpServerInfo.empty();

    public StdioClient(String command, String... args) {
        this.command = command;
        this.args = Arrays.asList(args);
    }

    @Override
    public void initialize() throws Exception {
        ProcessBuilder pb = new ProcessBuilder();
        List<String> cmd = new ArrayList<>();
        cmd.add(command);
        cmd.addAll(args);
        pb.command(cmd);
        pb.redirectErrorStream(false);
        process = pb.start();
        reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
        writer = new BufferedWriter(new OutputStreamWriter(process.getOutputStream()));

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
        if (resp.result() != null && resp.result().has("serverInfo")) {
            JsonNode info = resp.result().get("serverInfo");
            serverInfo = new McpServerInfo(
                    info.path("name").asText(""),
                    info.path("version").asText(""));
        }
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
    public void close() throws Exception {
        if (process != null) {
            process.destroy();
        }
    }

    // -------------------------------------------------------------------------

    private JsonRpcResponse sendRequest(String method, JsonNode params) throws Exception {
        lock.lock();
        try {
            long id = nextId.incrementAndGet();
            JsonRpcRequest req = JsonRpcRequest.of(id, method, params);
            String json = mapper.writeValueAsString(req);
            writer.write(json);
            writer.newLine();
            writer.flush();
            String line = reader.readLine();
            if (line == null) {
                throw new RuntimeException("mcp: server closed stdout");
            }
            return mapper.readValue(line, JsonRpcResponse.class);
        } finally {
            lock.unlock();
        }
    }
}
