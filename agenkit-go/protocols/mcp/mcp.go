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

// mcpProtocolVersion is the MCP protocol revision this implementation
// speaks. A single named constant (agenkit#781) that both client.go and
// server.go import, rather than each repeating the literal, so a version
// bump touches one line and the two halves of the protocol cannot drift
// from each other within this language.
//
// 2025-11-25 is the latest *ratified* MCP revision whose initialize/
// tools/list/tools/call surface is additive over 2024-11-05 (agenkit#733:
// the 2026-07-28 revision removes the initialize handshake in favor of a
// stateless core that this package does not implement, so advertising that
// literal would claim a handshake the wire no longer has).
const mcpProtocolVersion = "2025-11-25"

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

	// ProtocolVersion is the MCP revision the server actually reported in
	// its initialize response (the top-level result.protocolVersion field —
	// not part of the wire "serverInfo" object, but carried here for a
	// single place callers can check it after Initialize()). Before
	// agenkit#781, the initialize decode target had no field for this value
	// at all, so encoding/json silently dropped it and a peer speaking a
	// different revision was indistinguishable from one speaking ours.
	ProtocolVersion string `json:"-"`
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
