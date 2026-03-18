package mcp

import (
	"context"
	"fmt"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// mcpToolAdapter bridges an MCPTool advertised by an MCP server to the
// agenkit.Tool interface so it can be used by any agenkit agent.
type mcpToolAdapter struct {
	client MCPClient
	tool   MCPTool
}

// Name implements agenkit.Tool.
func (a *mcpToolAdapter) Name() string { return a.tool.Name }

// Description implements agenkit.Tool.
func (a *mcpToolAdapter) Description() string { return a.tool.Description }

// Execute calls the tool on the MCP server and maps the result to agenkit.ToolResult.
func (a *mcpToolAdapter) Execute(ctx context.Context, params map[string]any) (*agenkit.ToolResult, error) {
	result, err := a.client.CallTool(ctx, a.tool.Name, params)
	if err != nil {
		return nil, fmt.Errorf("mcp tool %q: %w", a.tool.Name, err)
	}

	data := textContent(result.Content)
	if result.IsError {
		return agenkit.NewToolError(data), nil
	}
	return agenkit.NewToolResult(data), nil
}

// ToolsFromClient calls ListTools on the client and returns each MCP tool
// wrapped as an agenkit.Tool, ready to be passed to any agenkit agent.
//
// Example:
//
//	tools, err := mcp.ToolsFromClient(ctx, client)
//	agent := patterns.NewReActAgent(llm, tools)
func ToolsFromClient(ctx context.Context, client MCPClient) ([]agenkit.Tool, error) {
	mcpTools, err := client.ListTools(ctx)
	if err != nil {
		return nil, fmt.Errorf("mcp: list tools: %w", err)
	}

	tools := make([]agenkit.Tool, len(mcpTools))
	for i, t := range mcpTools {
		tools[i] = &mcpToolAdapter{client: client, tool: t}
	}
	return tools, nil
}
