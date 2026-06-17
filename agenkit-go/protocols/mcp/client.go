package mcp

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"sync"
	"sync/atomic"
)

const (
	mcpProtocolVersion = "2024-11-05"
	mcpClientVersion   = "0.82.0"
)

// mcpInitParams returns the serialised params for the MCP initialize request.
func mcpInitParams() (json.RawMessage, error) {
	return json.Marshal(map[string]interface{}{
		"protocolVersion": mcpProtocolVersion,
		"capabilities":    map[string]interface{}{},
		"clientInfo": map[string]interface{}{
			"name":    "agenkit",
			"version": mcpClientVersion,
		},
	})
}

// StdioConfig holds configuration for StdioClient.
type StdioConfig struct {
	// Command is the executable to spawn (e.g. "npx", "python").
	Command string

	// Args are the arguments passed to Command.
	Args []string

	// Env contains additional environment variables (KEY=VALUE format).
	// If empty the subprocess inherits the parent environment.
	Env []string
}

// StdioClient connects to an MCP server by spawning a subprocess and
// speaking JSON-RPC 2.0 over stdin/stdout.
type StdioClient struct {
	cmd        *exec.Cmd
	stdin      io.WriteCloser
	encoder    *json.Encoder
	decoder    *json.Decoder
	mu         sync.Mutex
	nextID     atomic.Int64
	serverInfo MCPServerInfo
}

// NewStdioClient spawns the subprocess described by cfg, performs the MCP
// initialize handshake, and returns a ready-to-use client.
func NewStdioClient(ctx context.Context, cfg StdioConfig) (*StdioClient, error) {
	cmd := exec.CommandContext(ctx, cfg.Command, cfg.Args...) //nolint:gosec
	if len(cfg.Env) > 0 {
		cmd.Env = cfg.Env
	}

	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, fmt.Errorf("mcp: stdin pipe: %w", err)
	}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, fmt.Errorf("mcp: stdout pipe: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("mcp: start subprocess: %w", err)
	}

	c := &StdioClient{
		cmd:     cmd,
		stdin:   stdin,
		encoder: json.NewEncoder(stdin),
		decoder: json.NewDecoder(stdout),
	}

	if err := c.Initialize(ctx); err != nil {
		_ = c.Close()
		return nil, err
	}

	return c, nil
}

// Initialize sends the MCP initialize request and stores server info.
func (c *StdioClient) Initialize(ctx context.Context) error {
	params, err := mcpInitParams()
	if err != nil {
		return fmt.Errorf("mcp: marshal initialize params: %w", err)
	}

	resp, err := c.sendRequest(ctx, "initialize", params)
	if err != nil {
		return fmt.Errorf("mcp: initialize: %w", err)
	}

	var result struct {
		ServerInfo MCPServerInfo `json:"serverInfo"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		return fmt.Errorf("mcp: decode initialize result: %w", err)
	}
	c.serverInfo = result.ServerInfo
	return nil
}

// ListTools sends the tools/list request and returns the server's tools.
func (c *StdioClient) ListTools(ctx context.Context) ([]MCPTool, error) {
	resp, err := c.sendRequest(ctx, "tools/list", nil)
	if err != nil {
		return nil, fmt.Errorf("mcp: tools/list: %w", err)
	}

	var result struct {
		Tools []MCPTool `json:"tools"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		return nil, fmt.Errorf("mcp: decode tools/list result: %w", err)
	}
	return result.Tools, nil
}

// CallTool invokes a tool by name with the given arguments.
func (c *StdioClient) CallTool(ctx context.Context, name string, args map[string]any) (*MCPToolResult, error) {
	params, err := json.Marshal(map[string]interface{}{
		"name":      name,
		"arguments": args,
	})
	if err != nil {
		return nil, fmt.Errorf("mcp: marshal tools/call params: %w", err)
	}

	resp, err := c.sendRequest(ctx, "tools/call", params)
	if err != nil {
		return nil, fmt.Errorf("mcp: tools/call: %w", err)
	}

	var result MCPToolResult
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		return nil, fmt.Errorf("mcp: decode tools/call result: %w", err)
	}
	return &result, nil
}

// ServerInfo returns information about the connected server.
func (c *StdioClient) ServerInfo() MCPServerInfo { return c.serverInfo }

// Close terminates the subprocess and releases resources.
func (c *StdioClient) Close() error {
	if err := c.stdin.Close(); err != nil {
		_ = c.cmd.Wait()
		return fmt.Errorf("mcp: close stdin: %w", err)
	}
	return c.cmd.Wait()
}

// sendRequest encodes a JSON-RPC request and decodes the response.
// The mutex serialises the full write→read cycle so concurrent callers
// never interleave their request/response pairs on the stdio pipe.
// Note: stdio I/O is not cancellable mid-operation; ctx is only checked
// before acquiring the lock.
func (c *StdioClient) sendRequest(ctx context.Context, method string, params json.RawMessage) (*jsonrpcResponse, error) {
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	default:
	}

	c.mu.Lock()
	defer c.mu.Unlock()

	id := c.nextID.Add(1)
	req := jsonrpcRequest{
		JSONRPC: "2.0",
		ID:      id,
		Method:  method,
		Params:  params,
	}

	if err := c.encoder.Encode(req); err != nil {
		return nil, fmt.Errorf("encode request: %w", err)
	}
	var resp jsonrpcResponse
	if err := c.decoder.Decode(&resp); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}
	if resp.Error != nil {
		return nil, fmt.Errorf("rpc error %d: %s", resp.Error.Code, resp.Error.Message)
	}
	return &resp, nil
}

// ─── HTTPClient ────────────────────────────────────────────────────────────────

// HTTPClient connects to an MCP server that accepts JSON-RPC 2.0 over HTTP.
type HTTPClient struct {
	baseURL    string
	http       *http.Client
	nextID     atomic.Int64
	mu         sync.Mutex
	serverInfo MCPServerInfo
}

// NewHTTPClient connects to the MCP HTTP server at baseURL, performs the
// initialize handshake, and returns a ready-to-use client.
func NewHTTPClient(ctx context.Context, baseURL string) (*HTTPClient, error) {
	c := &HTTPClient{
		baseURL: baseURL,
		http:    &http.Client{},
	}

	if err := c.Initialize(ctx); err != nil {
		return nil, err
	}
	return c, nil
}

// Initialize sends the MCP initialize request to the HTTP server.
func (c *HTTPClient) Initialize(ctx context.Context) error {
	params, err := mcpInitParams()
	if err != nil {
		return fmt.Errorf("mcp: marshal initialize params: %w", err)
	}

	resp, err := c.sendRequest(ctx, "initialize", params)
	if err != nil {
		return fmt.Errorf("mcp: initialize: %w", err)
	}

	var result struct {
		ServerInfo MCPServerInfo `json:"serverInfo"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		return fmt.Errorf("mcp: decode initialize result: %w", err)
	}
	c.serverInfo = result.ServerInfo
	return nil
}

// ListTools sends tools/list to the HTTP server.
func (c *HTTPClient) ListTools(ctx context.Context) ([]MCPTool, error) {
	resp, err := c.sendRequest(ctx, "tools/list", nil)
	if err != nil {
		return nil, fmt.Errorf("mcp: tools/list: %w", err)
	}

	var result struct {
		Tools []MCPTool `json:"tools"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		return nil, fmt.Errorf("mcp: decode tools/list result: %w", err)
	}
	return result.Tools, nil
}

// CallTool invokes a named tool via the HTTP server.
func (c *HTTPClient) CallTool(ctx context.Context, name string, args map[string]any) (*MCPToolResult, error) {
	params, err := json.Marshal(map[string]interface{}{
		"name":      name,
		"arguments": args,
	})
	if err != nil {
		return nil, fmt.Errorf("mcp: marshal tools/call params: %w", err)
	}

	resp, err := c.sendRequest(ctx, "tools/call", params)
	if err != nil {
		return nil, fmt.Errorf("mcp: tools/call: %w", err)
	}

	var result MCPToolResult
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		return nil, fmt.Errorf("mcp: decode tools/call result: %w", err)
	}
	return &result, nil
}

// ServerInfo returns information about the connected server.
func (c *HTTPClient) ServerInfo() MCPServerInfo { return c.serverInfo }

// Close is a no-op for HTTPClient (no persistent connection to close).
func (c *HTTPClient) Close() error { return nil }

// sendRequest posts a JSON-RPC 2.0 request to the HTTP server and decodes
// the response. The mutex serialises concurrent calls.
func (c *HTTPClient) sendRequest(ctx context.Context, method string, params json.RawMessage) (*jsonrpcResponse, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	id := c.nextID.Add(1)
	req := jsonrpcRequest{
		JSONRPC: "2.0",
		ID:      id,
		Method:  method,
		Params:  params,
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("encode request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("build http request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")

	httpResp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("http post: %w", err)
	}
	defer func() { _ = httpResp.Body.Close() }()

	var resp jsonrpcResponse
	if err := json.NewDecoder(httpResp.Body).Decode(&resp); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}
	if resp.Error != nil {
		return nil, fmt.Errorf("rpc error %d: %s", resp.Error.Code, resp.Error.Message)
	}
	return &resp, nil
}
