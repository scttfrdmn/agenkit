// Package mcp provides Model Context Protocol (MCP) support for agenkit agents.
//
// MCP is a JSON-RPC 2.0 based protocol for AI tool integrations used by
// Claude Code, Cursor, and thousands of community tools. This package
// provides both client and server implementations using stdlib only
// (no external MCP library required).
//
// # Client Usage
//
// Connect to an MCP server over stdio (subprocess):
//
//	cfg := mcp.StdioConfig{Command: "npx", Args: []string{"-y", "@modelcontextprotocol/server-filesystem", "/tmp"}}
//	client, err := mcp.NewStdioClient(ctx, cfg)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	defer client.Close()
//
//	tools, err := mcp.ToolsFromClient(ctx, client)
//	agent := patterns.NewReActAgent(llm, tools)
//
// Or connect over HTTP:
//
//	client, err := mcp.NewHTTPClient(ctx, "http://localhost:3000")
//
// # Server Usage
//
// Expose agenkit tools as an MCP server:
//
//	server := mcp.NewServer(mcp.ServerConfig{
//	    Name:    "my-agent",
//	    Version: "1.0.0",
//	    Tools:   myTools,
//	})
//	if err := server.ServeStdio(ctx); err != nil {
//	    log.Fatal(err)
//	}
package mcp

import (
	"context"
	"encoding/json"
	"strings"
)

// jsonrpcRequest is the JSON-RPC 2.0 request wire type.
type jsonrpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      int64           `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// jsonrpcResponse is the JSON-RPC 2.0 response wire type.
type jsonrpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      int64           `json:"id"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *jsonrpcError   `json:"error,omitempty"`
}

// jsonrpcError is the JSON-RPC 2.0 error object.
type jsonrpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// MCPTool describes a tool advertised by an MCP server.
type MCPTool struct {
	Name        string      `json:"name"`
	Description string      `json:"description"`
	InputSchema interface{} `json:"inputSchema,omitempty"`
}

// MCPContent is a single content block returned by a tool call.
type MCPContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

// MCPToolResult is the result of a tools/call RPC.
type MCPToolResult struct {
	Content []MCPContent `json:"content"`
	IsError bool         `json:"isError"`
}

// MCPServerInfo holds information about the connected MCP server.
type MCPServerInfo struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

// MCPClient is the interface satisfied by StdioClient and HTTPClient.
type MCPClient interface {
	// Initialize performs the MCP handshake with the server.
	Initialize(ctx context.Context) error

	// ListTools returns the tools advertised by the server.
	ListTools(ctx context.Context) ([]MCPTool, error)

	// CallTool invokes a named tool with the given arguments.
	CallTool(ctx context.Context, name string, args map[string]any) (*MCPToolResult, error)

	// ServerInfo returns the server's name and version (populated after Initialize).
	ServerInfo() MCPServerInfo

	// Close releases resources held by the client.
	Close() error
}

// textContent joins all text-type content blocks with a single space.
func textContent(contents []MCPContent) string {
	var parts []string
	for _, c := range contents {
		if c.Type == "text" && c.Text != "" {
			parts = append(parts, c.Text)
		}
	}
	return strings.Join(parts, " ")
}
