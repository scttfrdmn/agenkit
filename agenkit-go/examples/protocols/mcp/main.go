//go:build ignore

// MCP (Model Context Protocol) Example
//
// Demonstrates all four usage patterns for the agenkit MCP package:
//  1. StdioClient — connect to an MCP server via subprocess stdio
//  2. HTTPClient  — connect to an MCP server via HTTP
//  3. MCPServer   — expose agenkit tools as an MCP server
//  4. ToolsFromClient — bridge MCP tools into a ReActAgent
//
// None of the external servers need to be running; each section fails
// gracefully with an explanatory message.
//
// Run:
//
//	go run main.go
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/mcp"
)

// ─── 1. StdioClient demo ──────────────────────────────────────────────────────

func demoStdioClient(ctx context.Context) {
	fmt.Println("=== StdioClient demo ===")

	// This would normally be an installed MCP server, e.g.:
	//   npx -y @modelcontextprotocol/server-filesystem /tmp
	cfg := mcp.StdioConfig{
		Command: "npx",
		Args:    []string{"-y", "@modelcontextprotocol/server-filesystem", "/tmp"},
	}

	client, err := mcp.NewStdioClient(ctx, cfg)
	if err != nil {
		fmt.Printf("  StdioClient not available (server not installed): %v\n\n", err)
		return
	}
	defer func() {
		if err := client.Close(); err != nil {
			log.Printf("close stdio client: %v", err)
		}
	}()

	info := client.ServerInfo()
	fmt.Printf("  Connected: %s %s\n", info.Name, info.Version)

	tools, err := mcp.ToolsFromClient(ctx, client)
	if err != nil {
		fmt.Printf("  list tools: %v\n\n", err)
		return
	}
	fmt.Printf("  Available tools (%d):\n", len(tools))
	for _, t := range tools {
		fmt.Printf("    - %s: %s\n", t.Name(), t.Description())
	}
	fmt.Println()
}

// ─── 2. HTTPClient demo ───────────────────────────────────────────────────────

func demoHTTPClient(ctx context.Context) {
	fmt.Println("=== HTTPClient demo ===")

	client, err := mcp.NewHTTPClient(ctx, "http://localhost:3000")
	if err != nil {
		fmt.Printf("  HTTPClient not available (server not running): %v\n\n", err)
		return
	}
	defer func() {
		if err := client.Close(); err != nil {
			log.Printf("close http client: %v", err)
		}
	}()

	info := client.ServerInfo()
	fmt.Printf("  Connected: %s %s\n", info.Name, info.Version)

	tools, err := mcp.ToolsFromClient(ctx, client)
	if err != nil {
		fmt.Printf("  list tools: %v\n\n", err)
		return
	}
	fmt.Printf("  Available tools (%d):\n", len(tools))
	for _, t := range tools {
		fmt.Printf("    - %s: %s\n", t.Name(), t.Description())
	}
	fmt.Println()
}

// ─── 3. MCPServer demo ────────────────────────────────────────────────────────

// greetTool is a simple agenkit.Tool used to demonstrate the server.
type greetTool struct{}

func (g *greetTool) Name() string        { return "greet" }
func (g *greetTool) Description() string { return "Returns a greeting for the given name" }
func (g *greetTool) Execute(_ context.Context, params map[string]any) (*agenkit.ToolResult, error) {
	name, _ := params["name"].(string)
	if name == "" {
		name = "world"
	}
	return agenkit.NewToolResult(fmt.Sprintf("Hello, %s!", name)), nil
}

func demoServer() {
	fmt.Println("=== MCPServer demo ===")

	server := mcp.NewServer(mcp.ServerConfig{
		Name:    "agenkit-demo",
		Version: "0.82.0",
		Tools:   []agenkit.Tool{&greetTool{}},
	})

	fmt.Printf("  Server created: %q with 1 tool\n", "agenkit-demo")
	fmt.Println("  Tool: greet —", (&greetTool{}).Description())
	fmt.Println()

	// To actually serve over stdio you would call:
	//   server.ServeStdio(context.Background())
	// For this demo we just show the server is constructed correctly.
	_ = server
}

// ─── 4. ToolsFromClient demo ──────────────────────────────────────────────────

// mockClient satisfies mcp.MCPClient for the demo without a real server.
type mockClient struct{}

func (m *mockClient) Initialize(_ context.Context) error { return nil }
func (m *mockClient) ListTools(_ context.Context) ([]mcp.MCPTool, error) {
	return []mcp.MCPTool{
		{Name: "search", Description: "Search the web for a query"},
		{Name: "calculator", Description: "Evaluate a mathematical expression"},
	}, nil
}
func (m *mockClient) CallTool(_ context.Context, name string, args map[string]any) (*mcp.MCPToolResult, error) {
	return &mcp.MCPToolResult{
		Content: []mcp.MCPContent{{Type: "text", Text: fmt.Sprintf("result from %s(%v)", name, args)}},
	}, nil
}
func (m *mockClient) ServerInfo() mcp.MCPServerInfo {
	return mcp.MCPServerInfo{Name: "mock-server", Version: "1.0.0"}
}
func (m *mockClient) Close() error { return nil }

func demoToolsFromClient(ctx context.Context) {
	fmt.Println("=== ToolsFromClient demo ===")

	client := &mockClient{}
	tools, err := mcp.ToolsFromClient(ctx, client)
	if err != nil {
		log.Fatalf("ToolsFromClient: %v", err)
	}

	fmt.Printf("  Wrapped %d MCP tools as agenkit.Tool:\n", len(tools))
	for _, t := range tools {
		fmt.Printf("    - %s: %s\n", t.Name(), t.Description())
	}

	// Demonstrate calling a tool through the adapter.
	result, err := tools[0].Execute(ctx, map[string]any{"query": "Go MCP"})
	if err != nil {
		log.Fatalf("execute tool: %v", err)
	}
	fmt.Printf("  Execute search: success=%v data=%v\n", result.Success, result.Data)

	// These tools can be passed directly to any agenkit agent:
	//   agent := patterns.NewReActAgent(llm, tools)
	fmt.Println()
}

// ─── main ─────────────────────────────────────────────────────────────────────

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	fmt.Println("Agenkit MCP Support — v0.82.0 Examples")
	fmt.Println("========================================")
	fmt.Println()

	demoStdioClient(ctx)
	demoHTTPClient(ctx)
	demoServer()
	demoToolsFromClient(ctx)

	fmt.Println("Done.")
}
