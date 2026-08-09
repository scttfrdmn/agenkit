package mcp

import (
	"bytes"
	"context"
	"encoding/json"
	"log"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ─── interface compile-time checks ────────────────────────────────────────────

// TestMCPClientInterface verifies that both transport types satisfy MCPClient.
func TestMCPClientInterface(t *testing.T) {
	var _ MCPClient = &StdioClient{}
	var _ MCPClient = &HTTPClient{}
}

// ─── JSON-RPC wire types ───────────────────────────────────────────────────────

// TestJSONRPCRequestMarshal verifies that jsonrpcRequest marshals correctly.
func TestJSONRPCRequestMarshal(t *testing.T) {
	req := jsonrpcRequest{
		JSONRPC: "2.0",
		ID:      42,
		Method:  "tools/list",
	}
	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	s := string(data)
	if !strings.Contains(s, `"jsonrpc":"2.0"`) {
		t.Errorf("missing jsonrpc field: %s", s)
	}
	if !strings.Contains(s, `"id":42`) {
		t.Errorf("missing id field: %s", s)
	}
	if !strings.Contains(s, `"method":"tools/list"`) {
		t.Errorf("missing method field: %s", s)
	}
}

// TestJSONRPCResponseUnmarshal verifies round-trip for jsonrpcResponse.
func TestJSONRPCResponseUnmarshal(t *testing.T) {
	raw := `{"jsonrpc":"2.0","id":7,"result":{"ok":true}}`
	var resp jsonrpcResponse
	if err := json.Unmarshal([]byte(raw), &resp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if resp.JSONRPC != "2.0" {
		t.Errorf("JSONRPC: got %q want %q", resp.JSONRPC, "2.0")
	}
	if resp.ID != 7 {
		t.Errorf("ID: got %d want 7", resp.ID)
	}
	if resp.Error != nil {
		t.Errorf("Error should be nil, got %v", resp.Error)
	}
}

// ─── MCPTool ──────────────────────────────────────────────────────────────────

// TestMCPToolMarshal verifies MCPTool JSON round-trip.
func TestMCPToolMarshal(t *testing.T) {
	tool := MCPTool{Name: "read_file", Description: "Read a file from disk"}
	data, err := json.Marshal(tool)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var got MCPTool
	if err := json.Unmarshal(data, &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got.Name != tool.Name {
		t.Errorf("Name: got %q want %q", got.Name, tool.Name)
	}
	if got.Description != tool.Description {
		t.Errorf("Description: got %q want %q", got.Description, tool.Description)
	}
}

// ─── textContent ──────────────────────────────────────────────────────────────

// TestTextContent_Single verifies a single text block returns its text.
func TestTextContent_Single(t *testing.T) {
	contents := []MCPContent{{Type: "text", Text: "hello"}}
	got := textContent(contents)
	if got != "hello" {
		t.Errorf("got %q want %q", got, "hello")
	}
}

// TestTextContent_Multi verifies multiple text blocks are joined with a space.
func TestTextContent_Multi(t *testing.T) {
	contents := []MCPContent{
		{Type: "text", Text: "hello"},
		{Type: "text", Text: "world"},
	}
	got := textContent(contents)
	if got != "hello world" {
		t.Errorf("got %q want %q", got, "hello world")
	}
}

// ─── mock MCPClient ───────────────────────────────────────────────────────────

type mockMCPClient struct {
	tools      []MCPTool
	callResult *MCPToolResult
	callErr    error
	info       MCPServerInfo
}

func (m *mockMCPClient) Initialize(_ context.Context) error { return nil }
func (m *mockMCPClient) ListTools(_ context.Context) ([]MCPTool, error) {
	return m.tools, nil
}
func (m *mockMCPClient) CallTool(_ context.Context, _ string, _ map[string]any) (*MCPToolResult, error) {
	return m.callResult, m.callErr
}
func (m *mockMCPClient) ServerInfo() MCPServerInfo { return m.info }
func (m *mockMCPClient) Close() error              { return nil }

// ─── mcpToolAdapter ───────────────────────────────────────────────────────────

// TestMCPToolAdapterName verifies that the adapter returns the tool's name.
func TestMCPToolAdapterName(t *testing.T) {
	adapter := &mcpToolAdapter{
		client: &mockMCPClient{},
		tool:   MCPTool{Name: "echo", Description: "Echo input"},
	}
	if adapter.Name() != "echo" {
		t.Errorf("Name() = %q, want %q", adapter.Name(), "echo")
	}
}

// TestMCPToolAdapterDescription verifies that the adapter returns the tool's description.
func TestMCPToolAdapterDescription(t *testing.T) {
	adapter := &mcpToolAdapter{
		client: &mockMCPClient{},
		tool:   MCPTool{Name: "echo", Description: "Echo input"},
	}
	if adapter.Description() != "Echo input" {
		t.Errorf("Description() = %q, want %q", adapter.Description(), "Echo input")
	}
}

// TestMCPToolAdapterExecute_Success verifies successful tool execution mapping.
func TestMCPToolAdapterExecute_Success(t *testing.T) {
	mock := &mockMCPClient{
		callResult: &MCPToolResult{
			Content: []MCPContent{{Type: "text", Text: "result data"}},
			IsError: false,
		},
	}
	adapter := &mcpToolAdapter{client: mock, tool: MCPTool{Name: "mytool"}}

	result, err := adapter.Execute(context.Background(), map[string]any{"x": 1})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !result.Success {
		t.Errorf("expected Success=true")
	}
	if result.Data != "result data" {
		t.Errorf("Data = %q, want %q", result.Data, "result data")
	}
}

// TestMCPToolAdapterExecute_IsError verifies isError=true maps to Success=false.
func TestMCPToolAdapterExecute_IsError(t *testing.T) {
	mock := &mockMCPClient{
		callResult: &MCPToolResult{
			Content: []MCPContent{{Type: "text", Text: "something went wrong"}},
			IsError: true,
		},
	}
	adapter := &mcpToolAdapter{client: mock, tool: MCPTool{Name: "mytool"}}

	result, err := adapter.Execute(context.Background(), nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Success {
		t.Errorf("expected Success=false")
	}
	if result.Error != "something went wrong" {
		t.Errorf("Error = %q, want %q", result.Error, "something went wrong")
	}
}

// TestToolsFromClient verifies that ToolsFromClient wraps each MCPTool as an agenkit.Tool.
func TestToolsFromClient(t *testing.T) {
	mock := &mockMCPClient{
		tools: []MCPTool{
			{Name: "tool_a", Description: "Tool A"},
			{Name: "tool_b", Description: "Tool B"},
		},
	}

	tools, err := ToolsFromClient(context.Background(), mock)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(tools) != 2 {
		t.Fatalf("expected 2 tools, got %d", len(tools))
	}
	if tools[0].Name() != "tool_a" {
		t.Errorf("tools[0].Name() = %q, want %q", tools[0].Name(), "tool_a")
	}
	if tools[1].Name() != "tool_b" {
		t.Errorf("tools[1].Name() = %q, want %q", tools[1].Name(), "tool_b")
	}
}

// ─── MCPServer ────────────────────────────────────────────────────────────────

// echoTool is a minimal agenkit.Tool used to test the server.
type echoTool struct{}

func (e *echoTool) Name() string        { return "echo" }
func (e *echoTool) Description() string { return "Echoes the input message" }
func (e *echoTool) Execute(_ context.Context, params map[string]any) (*agenkit.ToolResult, error) {
	msg, _ := params["message"].(string)
	return agenkit.NewToolResult(msg), nil
}

// TestMCPServerHandleRequest exercises initialize, tools/list, and tools/call
// through the in-memory handleRequest dispatcher.
func TestMCPServerHandleRequest(t *testing.T) {
	server := NewServer(ServerConfig{
		Name:    "test-server",
		Version: "1.0.0",
		Tools:   []agenkit.Tool{&echoTool{}},
	})
	ctx := context.Background()

	// initialize
	initReq := jsonrpcRequest{JSONRPC: "2.0", ID: 1, Method: "initialize"}
	initResp := server.handleRequest(ctx, initReq)
	if initResp.Error != nil {
		t.Fatalf("initialize error: %v", initResp.Error)
	}
	var initResult struct {
		ServerInfo MCPServerInfo `json:"serverInfo"`
	}
	if err := json.Unmarshal(initResp.Result, &initResult); err != nil {
		t.Fatalf("decode initialize result: %v", err)
	}
	if initResult.ServerInfo.Name != "test-server" {
		t.Errorf("serverInfo.name = %q, want %q", initResult.ServerInfo.Name, "test-server")
	}

	// tools/list
	listReq := jsonrpcRequest{JSONRPC: "2.0", ID: 2, Method: "tools/list"}
	listResp := server.handleRequest(ctx, listReq)
	if listResp.Error != nil {
		t.Fatalf("tools/list error: %v", listResp.Error)
	}
	var listResult struct {
		Tools []MCPTool `json:"tools"`
	}
	if err := json.Unmarshal(listResp.Result, &listResult); err != nil {
		t.Fatalf("decode tools/list result: %v", err)
	}
	if len(listResult.Tools) != 1 || listResult.Tools[0].Name != "echo" {
		t.Errorf("expected [echo], got %v", listResult.Tools)
	}

	// tools/call
	callParams, _ := json.Marshal(map[string]interface{}{
		"name":      "echo",
		"arguments": map[string]interface{}{"message": "hello MCP"},
	})
	callReq := jsonrpcRequest{JSONRPC: "2.0", ID: 3, Method: "tools/call", Params: callParams}
	callResp := server.handleRequest(ctx, callReq)
	if callResp.Error != nil {
		t.Fatalf("tools/call error: %v", callResp.Error)
	}
	var toolResult MCPToolResult
	if err := json.Unmarshal(callResp.Result, &toolResult); err != nil {
		t.Fatalf("decode tools/call result: %v", err)
	}
	if toolResult.IsError {
		t.Errorf("expected IsError=false")
	}
	if len(toolResult.Content) == 0 || toolResult.Content[0].Text != "hello MCP" {
		t.Errorf("expected content text %q, got %v", "hello MCP", toolResult.Content)
	}
}

// ─── Protocol version negotiation (agenkit#781) ────────────────────────────────

// TestMCPServerInitializeAdvertisesSharedConstant checks the server's
// advertised protocolVersion is the shared mcpProtocolVersion constant, not
// an independent literal that could drift from the client's.
func TestMCPServerInitializeAdvertisesSharedConstant(t *testing.T) {
	server := NewServer(ServerConfig{Name: "test-server", Version: "1.0.0"})
	ctx := context.Background()

	initReq := jsonrpcRequest{JSONRPC: "2.0", ID: 1, Method: "initialize"}
	initResp := server.handleRequest(ctx, initReq)
	if initResp.Error != nil {
		t.Fatalf("initialize error: %v", initResp.Error)
	}
	var result struct {
		ProtocolVersion string `json:"protocolVersion"`
	}
	if err := json.Unmarshal(initResp.Result, &result); err != nil {
		t.Fatalf("decode initialize result: %v", err)
	}
	if result.ProtocolVersion != mcpProtocolVersion {
		t.Errorf("protocolVersion = %q, want %q", result.ProtocolVersion, mcpProtocolVersion)
	}
}

// TestMCPServerWarnsOnClientVersionMismatch is the negative-verification
// target for agenkit#781: reverting the mismatch check added to
// handleInitialize (removing the log.Printf call) makes this test fail,
// because nothing else in the server reads req.Params for "protocolVersion".
func TestMCPServerWarnsOnClientVersionMismatch(t *testing.T) {
	var buf bytes.Buffer
	orig := log.Writer()
	log.SetOutput(&buf)
	defer log.SetOutput(orig)

	server := NewServer(ServerConfig{Name: "test-server", Version: "1.0.0"})
	ctx := context.Background()

	params, err := json.Marshal(map[string]interface{}{
		"protocolVersion": "1999-01-01",
		"capabilities":    map[string]interface{}{},
	})
	if err != nil {
		t.Fatalf("marshal params: %v", err)
	}
	initReq := jsonrpcRequest{JSONRPC: "2.0", ID: 1, Method: "initialize", Params: params}
	initResp := server.handleRequest(ctx, initReq)
	if initResp.Error != nil {
		t.Fatalf("initialize error: %v", initResp.Error)
	}

	// Server still answers with the version it actually speaks.
	var result struct {
		ProtocolVersion string `json:"protocolVersion"`
	}
	if err := json.Unmarshal(initResp.Result, &result); err != nil {
		t.Fatalf("decode initialize result: %v", err)
	}
	if result.ProtocolVersion != mcpProtocolVersion {
		t.Errorf("protocolVersion = %q, want %q", result.ProtocolVersion, mcpProtocolVersion)
	}

	logged := buf.String()
	if !strings.Contains(logged, "1999-01-01") || !strings.Contains(logged, mcpProtocolVersion) {
		t.Errorf("expected a version-mismatch warning mentioning both versions, got: %q", logged)
	}
}

// TestMCPServerNoWarningOnMatchingClientVersion checks that a client
// requesting the server's own version produces no mismatch warning.
func TestMCPServerNoWarningOnMatchingClientVersion(t *testing.T) {
	var buf bytes.Buffer
	orig := log.Writer()
	log.SetOutput(&buf)
	defer log.SetOutput(orig)

	server := NewServer(ServerConfig{Name: "test-server", Version: "1.0.0"})
	ctx := context.Background()

	params, err := json.Marshal(map[string]interface{}{
		"protocolVersion": mcpProtocolVersion,
		"capabilities":    map[string]interface{}{},
	})
	if err != nil {
		t.Fatalf("marshal params: %v", err)
	}
	initReq := jsonrpcRequest{JSONRPC: "2.0", ID: 1, Method: "initialize", Params: params}
	if resp := server.handleRequest(ctx, initReq); resp.Error != nil {
		t.Fatalf("initialize error: %v", resp.Error)
	}

	if logged := buf.String(); strings.Contains(logged, "protocol version") {
		t.Errorf("expected no mismatch warning, got: %q", logged)
	}
}

// TestParseInitializeResultCapturesProtocolVersion checks that the client's
// server_info now exposes the server's reported protocolVersion. Before
// agenkit#781, the decode target had no field for this and the value was
// silently dropped by encoding/json.
func TestParseInitializeResultCapturesProtocolVersion(t *testing.T) {
	raw := json.RawMessage(`{"protocolVersion":"` + mcpProtocolVersion + `","serverInfo":{"name":"srv","version":"9.9.9"}}`)
	info, err := parseInitializeResult(raw)
	if err != nil {
		t.Fatalf("parseInitializeResult: %v", err)
	}
	if info.ProtocolVersion != mcpProtocolVersion {
		t.Errorf("ProtocolVersion = %q, want %q", info.ProtocolVersion, mcpProtocolVersion)
	}
	if info.Name != "srv" || info.Version != "9.9.9" {
		t.Errorf("unexpected server info: %+v", info)
	}
}

// TestParseInitializeResultWarnsOnServerVersionMismatch is the
// negative-verification target for the client-side half of agenkit#781:
// reverting the mismatch check in parseInitializeResult (removing the
// log.Printf call) makes this test fail — ProtocolVersion would still
// populate (independently covered above), but no warning would be logged.
func TestParseInitializeResultWarnsOnServerVersionMismatch(t *testing.T) {
	var buf bytes.Buffer
	orig := log.Writer()
	log.SetOutput(&buf)
	defer log.SetOutput(orig)

	raw := json.RawMessage(`{"protocolVersion":"1999-01-01","serverInfo":{"name":"old-server","version":"0.1.0"}}`)
	info, err := parseInitializeResult(raw)
	if err != nil {
		t.Fatalf("parseInitializeResult: %v", err)
	}
	if info.ProtocolVersion != "1999-01-01" {
		t.Errorf("ProtocolVersion = %q, want %q", info.ProtocolVersion, "1999-01-01")
	}

	logged := buf.String()
	if !strings.Contains(logged, "1999-01-01") || !strings.Contains(logged, mcpProtocolVersion) {
		t.Errorf("expected a version-mismatch warning mentioning both versions, got: %q", logged)
	}
}
