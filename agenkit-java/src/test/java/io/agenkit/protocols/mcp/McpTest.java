package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.agenkit.core.Tool;
import io.agenkit.core.ToolResult;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

class McpTest {

    // -------------------------------------------------------------------------
    // Mock client used by multiple tests
    // -------------------------------------------------------------------------

    static class MockMcpClient implements McpClient {

        private final List<McpTool> tools;
        private boolean callReturnsError = false;

        MockMcpClient(List<McpTool> tools) {
            this.tools = tools;
        }

        MockMcpClient withCallError(boolean flag) {
            this.callReturnsError = flag;
            return this;
        }

        @Override public void initialize() {}

        @Override public List<McpTool> listTools() {
            return tools;
        }

        @Override public McpToolResult callTool(String name, Map<String, Object> args) {
            return new McpToolResult(List.of(new McpContent("text", "result")), callReturnsError);
        }

        @Override public McpServerInfo serverInfo() {
            return McpServerInfo.empty();
        }

        @Override public void close() {}
    }

    // -------------------------------------------------------------------------
    // Wire-type serialisation
    // -------------------------------------------------------------------------

    @Test
    void jsonRpcRequestSerializes() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        var params = mapper.createObjectNode().put("key", "value");
        JsonRpcRequest req = JsonRpcRequest.of(1L, "tools/list", params);
        String json = mapper.writeValueAsString(req);

        assertThat(json).contains("\"jsonrpc\":\"2.0\"");
        assertThat(json).contains("\"id\":1");
        assertThat(json).contains("\"method\":\"tools/list\"");
    }

    @Test
    void jsonRpcResponseDeserializes() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        String json = "{\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"ok\":true},\"error\":null}";
        JsonRpcResponse resp = mapper.readValue(json, JsonRpcResponse.class);

        assertThat(resp.jsonrpc()).isEqualTo("2.0");
        assertThat(resp.id()).isEqualTo(2L);
        assertThat(resp.result().get("ok").asBoolean()).isTrue();
        assertThat(resp.error()).isNull();
    }

    @Test
    void jsonRpcErrorDeserializes() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        String json = "{\"code\":-32601,\"message\":\"method not found\"}";
        JsonRpcError err = mapper.readValue(json, JsonRpcError.class);

        assertThat(err.code()).isEqualTo(-32601);
        assertThat(err.message()).isEqualTo("method not found");
    }

    // -------------------------------------------------------------------------
    // Domain-type round-trips
    // -------------------------------------------------------------------------

    @Test
    void mcpToolRoundTrips() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        McpTool tool = new McpTool("my-tool", "does things");
        String json = mapper.writeValueAsString(tool);
        McpTool parsed = mapper.readValue(json, McpTool.class);

        assertThat(parsed.name()).isEqualTo("my-tool");
        assertThat(parsed.description()).isEqualTo("does things");
    }

    @Test
    void mcpServerInfoEmpty() {
        McpServerInfo info = McpServerInfo.empty();
        assertThat(info.name()).isEmpty();
        assertThat(info.version()).isEmpty();
    }

    // -------------------------------------------------------------------------
    // McpToolResult.textContent
    // -------------------------------------------------------------------------

    @Test
    void textContentSingleBlock() {
        List<McpContent> contents = List.of(new McpContent("text", "hello world"));
        assertThat(McpToolResult.textContent(contents)).isEqualTo("hello world");
    }

    @Test
    void textContentMultipleBlocks() {
        List<McpContent> contents = List.of(
                new McpContent("text", "foo"),
                new McpContent("text", "bar"));
        assertThat(McpToolResult.textContent(contents)).isEqualTo("foo bar");
    }

    @Test
    void textContentIgnoresNonTextBlocks() {
        List<McpContent> contents = List.of(
                new McpContent("image", "data"),
                new McpContent("text", "visible"));
        assertThat(McpToolResult.textContent(contents)).isEqualTo("visible");
    }

    @Test
    void textContentIgnoresNullText() {
        List<McpContent> contents = List.of(
                new McpContent("text", null),
                new McpContent("text", "kept"));
        assertThat(McpToolResult.textContent(contents)).isEqualTo("kept");
    }

    // -------------------------------------------------------------------------
    // Client interface compliance
    // -------------------------------------------------------------------------

    @Test
    void stdioClientImplementsMcpClient() {
        McpClient client = new StdioClient("echo");
        assertThat(client).isInstanceOf(McpClient.class);
        assertThat(client).isInstanceOf(AutoCloseable.class);
    }

    @Test
    void httpClientImplementsMcpClient() {
        McpClient client = new McpHttpClient("http://localhost:8080");
        assertThat(client).isInstanceOf(McpClient.class);
        assertThat(client).isInstanceOf(AutoCloseable.class);
    }

    @Test
    void mockClientCloseDoesNotThrow() {
        MockMcpClient client = new MockMcpClient(List.of());
        assertThatCode(client::close).doesNotThrowAnyException();
    }

    // -------------------------------------------------------------------------
    // McpToolAdapter
    // -------------------------------------------------------------------------

    @Test
    void adapterName() {
        MockMcpClient client = new MockMcpClient(List.of());
        McpToolAdapter adapter = new McpToolAdapter(client, new McpTool("my-tool", "desc"));
        assertThat(adapter.getName()).isEqualTo("my-tool");
    }

    @Test
    void adapterDescription() {
        MockMcpClient client = new MockMcpClient(List.of());
        McpToolAdapter adapter = new McpToolAdapter(client, new McpTool("t", "a helpful tool"));
        assertThat(adapter.getDescription()).isEqualTo("a helpful tool");
    }

    @Test
    void adapterExecuteSuccess() throws Exception {
        MockMcpClient client = new MockMcpClient(List.of()).withCallError(false);
        McpToolAdapter adapter = new McpToolAdapter(client, new McpTool("t", "d"));
        CompletableFuture<ToolResult> future = adapter.execute(Map.of());
        ToolResult result = future.get();
        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getData()).isEqualTo("result");
    }

    @Test
    void adapterExecuteIsError() throws Exception {
        MockMcpClient client = new MockMcpClient(List.of()).withCallError(true);
        McpToolAdapter adapter = new McpToolAdapter(client, new McpTool("t", "d"));
        CompletableFuture<ToolResult> future = adapter.execute(Map.of());
        ToolResult result = future.get();
        assertThat(result.isSuccess()).isFalse();
        assertThat(result.getError()).isEqualTo("result");
    }

    // -------------------------------------------------------------------------
    // McpTools factory
    // -------------------------------------------------------------------------

    @Test
    void fromClientWrapsTools() throws Exception {
        List<McpTool> mcpTools = List.of(
                new McpTool("tool-a", "does a"),
                new McpTool("tool-b", "does b"));
        MockMcpClient client = new MockMcpClient(mcpTools);

        List<Tool> tools = McpTools.fromClient(client);

        assertThat(tools).hasSize(2);
        assertThat(tools.get(0).getName()).isEqualTo("tool-a");
        assertThat(tools.get(1).getName()).isEqualTo("tool-b");
    }

    @Test
    void fromClientEmptyList() throws Exception {
        MockMcpClient client = new MockMcpClient(List.of());
        List<Tool> tools = McpTools.fromClient(client);
        assertThat(tools).isEmpty();
    }

    // -------------------------------------------------------------------------
    // McpServer request handling
    // -------------------------------------------------------------------------

    @Test
    void serverHandlesInitialize() throws Exception {
        McpServer server = new McpServer("test-server", "1.0.0", List.of());
        ObjectMapper mapper = new ObjectMapper();
        JsonRpcRequest req = JsonRpcRequest.of(1L, "initialize", mapper.createObjectNode());
        JsonRpcResponse resp = server.handleRequest(req);

        assertThat(resp.error()).isNull();
        assertThat(resp.result().path("serverInfo").path("name").asText()).isEqualTo("test-server");
        assertThat(resp.result().path("serverInfo").path("version").asText()).isEqualTo("1.0.0");
    }

    @Test
    void serverHandlesToolsList() throws Exception {
        io.agenkit.core.Tool fakeTool = new io.agenkit.core.Tool() {
            @Override public String getName() { return "hello"; }
            @Override public String getDescription() { return "says hello"; }
            @Override public CompletableFuture<ToolResult> execute(Map<String, Object> p) {
                return CompletableFuture.completedFuture(ToolResult.ok("hi"));
            }
        };
        McpServer server = new McpServer("s", "1", List.of(fakeTool));
        ObjectMapper mapper = new ObjectMapper();
        JsonRpcRequest req = JsonRpcRequest.of(2L, "tools/list", mapper.createObjectNode());
        JsonRpcResponse resp = server.handleRequest(req);

        assertThat(resp.error()).isNull();
        var tools = resp.result().path("tools");
        assertThat(tools.isArray()).isTrue();
        assertThat(tools.size()).isEqualTo(1);
        assertThat(tools.get(0).path("name").asText()).isEqualTo("hello");
    }

    @Test
    void serverReturnsMethodNotFound() throws Exception {
        McpServer server = new McpServer("s", "1", List.of());
        ObjectMapper mapper = new ObjectMapper();
        JsonRpcRequest req = JsonRpcRequest.of(3L, "unknown/method", mapper.createObjectNode());
        JsonRpcResponse resp = server.handleRequest(req);

        assertThat(resp.error()).isNotNull();
        assertThat(resp.error().code()).isEqualTo(-32601);
        assertThat(resp.error().message()).contains("method not found");
    }

    @Test
    void serverHandlesToolsCall() throws Exception {
        io.agenkit.core.Tool fakeTool = new io.agenkit.core.Tool() {
            @Override public String getName() { return "greet"; }
            @Override public String getDescription() { return "greets user"; }
            @Override public CompletableFuture<ToolResult> execute(Map<String, Object> p) {
                return CompletableFuture.completedFuture(ToolResult.ok("hello"));
            }
        };
        McpServer server = new McpServer("s", "1", List.of(fakeTool));
        ObjectMapper mapper = new ObjectMapper();
        var params = mapper.createObjectNode().put("name", "greet");
        params.set("arguments", mapper.createObjectNode());
        JsonRpcRequest req = JsonRpcRequest.of(4L, "tools/call", params);
        JsonRpcResponse resp = server.handleRequest(req);

        assertThat(resp.error()).isNull();
        assertThat(resp.result().path("isError").asBoolean()).isFalse();
        assertThat(resp.result().path("content").get(0).path("text").asText()).isEqualTo("hello");
    }
}
