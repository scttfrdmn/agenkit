// Test server for integration testing
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/agenkit/agenkit-go/adapter/http"
	"github.com/agenkit/agenkit-go/agenkit"
)

// EchoAgent is a simple echo agent for testing.
type EchoAgent struct{}

func (a *EchoAgent) Name() string {
	return "echo"
}

func (a *EchoAgent) Capabilities() []string {
	return []string{"echo"}
}

func (a *EchoAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{
		Role:    "agent",
		Content: fmt.Sprintf("Echo: %s", message.Content),
		Metadata: map[string]interface{}{
			"original": message.Content,
			"language": "go",
		},
	}, nil
}

func main() {
	port := flag.Int("port", 8081, "Port to listen on")
	protocol := flag.String("protocol", "http", "Protocol to use (http, http2, http3)")
	flag.Parse()

	agent := &EchoAgent{}

	// Configure server options based on protocol
	addr := fmt.Sprintf("0.0.0.0:%d", *port)
	options := http.ServerOptions{
		EnableHTTP2: *protocol == "http2",
		EnableHTTP3: *protocol == "http3",
	}

	// Create HTTP server
	server := http.NewHTTPAgentWithOptions(agent, addr, options)

	// Start server in goroutine
	ctx := context.Background()
	go func() {
		if err := server.Start(ctx); err != nil {
			log.Printf("Server error: %v", err)
		}
	}()

	fmt.Printf("Go server listening on http://%s (protocol: %s)\n", addr, *protocol)
	fmt.Fprintf(os.Stderr, "Server started successfully\n")

	// Wait for interrupt signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	<-sigChan

	fmt.Println("\nShutting down server...")
	server.Stop()
}
