package mcp

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ServerConfig holds configuration for MCPServer.
type ServerConfig struct {
	// Name is the server name advertised during the initialize handshake.
	Name string

	// Version is the server version advertised during the initialize handshake.
	Version string

	// Tools are the agenkit tools exposed via this server.
	Tools []agenkit.Tool
}

// MCPServer exposes agenkit tools as an MCP stdio server.
//
// Handles the JSON-RPC 2.0 methods required by the MCP spec:
//   - initialize: returns server info and capabilities
//   - tools/list: returns the list of available tools
//   - tools/call: executes a tool and returns the result
type MCPServer struct {
	config ServerConfig
	tools  map[string]agenkit.Tool
}

// NewServer creates a new MCPServer with the given configuration.
func NewServer(cfg ServerConfig) *MCPServer {
	tools := make(map[string]agenkit.Tool, len(cfg.Tools))
	for _, t := range cfg.Tools {
		tools[t.Name()] = t
	}
	return &MCPServer{config: cfg, tools: tools}
}

// ServeStdio reads JSON-RPC 2.0 requests from os.Stdin and writes responses
// to os.Stdout. Runs until ctx is cancelled or stdin is closed.
func (s *MCPServer) ServeStdio(ctx context.Context) error {
	encoder := json.NewEncoder(os.Stdout)
	scanner := bufio.NewScanner(os.Stdin)

	for {
		// Check for cancellation before blocking on next line.
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		if !scanner.Scan() {
			if err := scanner.Err(); err != nil {
				return fmt.Errorf("mcp server: stdin: %w", err)
			}
			return nil // stdin closed — clean shutdown
		}

		var req jsonrpcRequest
		if err := json.Unmarshal(scanner.Bytes(), &req); err != nil {
			// Malformed request: send parse error and continue.
			resp := jsonrpcResponse{
				JSONRPC: "2.0",
				Error:   &jsonrpcError{Code: -32700, Message: "parse error"},
			}
			if err := encoder.Encode(resp); err != nil {
				return fmt.Errorf("mcp server: encode error response: %w", err)
			}
			continue
		}

		resp := s.handleRequest(ctx, req)
		if err := encoder.Encode(resp); err != nil {
			return fmt.Errorf("mcp server: encode response: %w", err)
		}
	}
}

// handleRequest dispatches a single JSON-RPC request and returns the response.
// It is exported for direct use in tests.
func (s *MCPServer) handleRequest(ctx context.Context, req jsonrpcRequest) jsonrpcResponse {
	switch req.Method {
	case "initialize":
		return s.handleInitialize(req)
	case "tools/list":
		return s.handleToolsList(req)
	case "tools/call":
		return s.handleToolsCall(ctx, req)
	default:
		return jsonrpcResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error:   &jsonrpcError{Code: -32601, Message: fmt.Sprintf("method not found: %s", req.Method)},
		}
	}
}

func (s *MCPServer) handleInitialize(req jsonrpcRequest) jsonrpcResponse {
	// Read (and thus stop discarding) the client's requested version —
	// agenkit#781. Per the MCP spec's negotiation model the server always
	// replies with the revision it actually implements; a mismatch is
	// logged so version skew is visible instead of silent.
	var params struct {
		ProtocolVersion string `json:"protocolVersion"`
	}
	if len(req.Params) > 0 {
		if err := json.Unmarshal(req.Params, &params); err == nil &&
			params.ProtocolVersion != "" && params.ProtocolVersion != mcpProtocolVersion {
			log.Printf("mcp: client requested protocol version %q, server speaks %q",
				params.ProtocolVersion, mcpProtocolVersion)
		}
	}

	result, err := json.Marshal(map[string]interface{}{
		"protocolVersion": mcpProtocolVersion,
		"capabilities": map[string]interface{}{
			"tools": map[string]interface{}{},
		},
		"serverInfo": MCPServerInfo{
			Name:    s.config.Name,
			Version: s.config.Version,
		},
	})
	if err != nil {
		return s.internalError(req.ID, err)
	}
	return jsonrpcResponse{JSONRPC: "2.0", ID: req.ID, Result: result}
}

func (s *MCPServer) handleToolsList(req jsonrpcRequest) jsonrpcResponse {
	tools := make([]MCPTool, 0, len(s.config.Tools))
	for _, t := range s.config.Tools {
		tools = append(tools, MCPTool{
			Name:        t.Name(),
			Description: t.Description(),
		})
	}

	result, err := json.Marshal(map[string]interface{}{"tools": tools})
	if err != nil {
		return s.internalError(req.ID, err)
	}
	return jsonrpcResponse{JSONRPC: "2.0", ID: req.ID, Result: result}
}

func (s *MCPServer) handleToolsCall(ctx context.Context, req jsonrpcRequest) jsonrpcResponse {
	var params struct {
		Name      string         `json:"name"`
		Arguments map[string]any `json:"arguments"`
	}
	if err := json.Unmarshal(req.Params, &params); err != nil {
		return jsonrpcResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error:   &jsonrpcError{Code: -32602, Message: "invalid params"},
		}
	}

	tool, ok := s.tools[params.Name]
	if !ok {
		return jsonrpcResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error:   &jsonrpcError{Code: -32602, Message: fmt.Sprintf("unknown tool: %s", params.Name)},
		}
	}

	toolResult, err := tool.Execute(ctx, params.Arguments)
	if err != nil {
		// Execution error → isError=true content block.
		result, merr := json.Marshal(MCPToolResult{
			Content: []MCPContent{{Type: "text", Text: err.Error()}},
			IsError: true,
		})
		if merr != nil {
			return s.internalError(req.ID, merr)
		}
		return jsonrpcResponse{JSONRPC: "2.0", ID: req.ID, Result: result}
	}

	isError := !toolResult.Success
	text := fmt.Sprintf("%v", toolResult.Data)
	if isError && toolResult.Error != "" {
		text = toolResult.Error
	}

	result, merr := json.Marshal(MCPToolResult{
		Content: []MCPContent{{Type: "text", Text: text}},
		IsError: isError,
	})
	if merr != nil {
		return s.internalError(req.ID, merr)
	}
	return jsonrpcResponse{JSONRPC: "2.0", ID: req.ID, Result: result}
}

func (s *MCPServer) internalError(id int64, err error) jsonrpcResponse {
	return jsonrpcResponse{
		JSONRPC: "2.0",
		ID:      id,
		Error:   &jsonrpcError{Code: -32603, Message: fmt.Sprintf("internal error: %v", err)},
	}
}
