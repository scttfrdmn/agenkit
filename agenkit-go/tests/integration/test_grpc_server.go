// Package main provides a simple gRPC test server for cross-language integration tests.
//
// This server can be run standalone for testing Python clients against Go servers.
//
// Usage:
//
//	go run test_grpc_server.go [port]
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strconv"
	"syscall"

	"github.com/agenkit/agenkit-go/adapter/grpc"
	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/observability"
)

// CrossLanguageTestAgent is a test agent for cross-language integration tests.
type CrossLanguageTestAgent struct{}

// Name returns the agent name.
func (a *CrossLanguageTestAgent) Name() string {
	return "cross-language-test-agent"
}

// Capabilities returns the agent capabilities.
func (a *CrossLanguageTestAgent) Capabilities() []string {
	return []string{"echo", "metadata", "unicode", "streaming"}
}

// Process echoes the message back with metadata.
func (a *CrossLanguageTestAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{
		Role:    "agent",
		Content: fmt.Sprintf("Echo: %s", message.Content),
		Metadata: map[string]interface{}{
			"original_content":  message.Content,
			"original_role":     message.Role,
			"original_metadata": message.Metadata,
			"server_language":   "go",
			"server_name":       a.Name(),
		},
	}, nil
}

func main() {
	// Get port from command line or use default
	port := 50051
	if len(os.Args) > 1 {
		var err error
		port, err = strconv.Atoi(os.Args[1])
		if err != nil {
			log.Fatalf("Invalid port: %v", err)
		}
	}

	// Initialize tracing (no exporters for test server, just W3C propagation)
	_, err := observability.InitTracing("test-grpc-server", "", false)
	if err != nil {
		log.Printf("Warning: Failed to initialize tracing: %v", err)
	}

	// Create agent and wrap with tracing middleware
	agent := &CrossLanguageTestAgent{}
	tracedAgent := observability.NewTracingMiddleware(agent, "")

	// Create gRPC server wrapper
	addr := fmt.Sprintf("localhost:%d", port)
	server, err := grpc.NewGRPCServer(tracedAgent, addr)
	if err != nil {
		log.Fatalf("Failed to create gRPC server: %v", err)
	}

	fmt.Printf("Starting Go gRPC test server on port %d...\n", port)
	fmt.Printf("Agent: %s\n", agent.Name())
	fmt.Printf("Capabilities: %v\n", agent.Capabilities())
	fmt.Println("Tracing enabled for cross-language observability tests")
	fmt.Println("Press Ctrl+C to stop")

	// Start server
	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}

	// Wait for interrupt signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	<-sigChan

	fmt.Println("\nShutting down...")
	if err := server.Stop(); err != nil {
		log.Printf("Error stopping server: %v", err)
	}

	// Shutdown tracing
	if err := observability.Shutdown(context.Background()); err != nil {
		log.Printf("Error shutting down tracing: %v", err)
	}
}
