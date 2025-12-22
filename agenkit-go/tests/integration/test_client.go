//go:build ignore

// Package main provides a simple test client for cross-language integration tests.
//
// This client can be used to test Go client → Python server communication.
//
// Usage:
//
//	go run test_client.go -url tcp://localhost:8080 -message "Hello from Go"
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/remote"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

func main() {
	// Parse command line flags
	url := flag.String("url", "", "Server URL (e.g., tcp://localhost:8080)")
	message := flag.String("message", "Hello from Go client", "Message to send")
	flag.Parse()

	if *url == "" {
		log.Fatal("Error: -url flag is required")
	}

	// Create remote agent with proper API
	agent, err := remote.NewRemoteAgent("test-client", *url, 10*time.Second)
	if err != nil {
		log.Fatalf("Failed to create remote agent: %v", err)
	}

	// Create message
	msg := &agenkit.Message{
		Role:    "user",
		Content: *message,
		Metadata: map[string]interface{}{
			"client_language": "go",
			"test":            true,
		},
	}

	// Send message to server
	ctx := context.Background()
	response, err := agent.Process(ctx, msg)
	if err != nil {
		log.Fatalf("Failed to send message: %v", err)
	}

	// Print response
	fmt.Printf("Response from server:\n")
	fmt.Printf("  Role: %s\n", response.Role)
	fmt.Printf("  Content: %s\n", response.Content)
	if len(response.Metadata) > 0 {
		fmt.Printf("  Metadata: %v\n", response.Metadata)
	}

	// Check for expected server language in metadata
	if serverLang, ok := response.Metadata["language"].(string); ok {
		fmt.Printf("  Server language: %s\n", serverLang)
	}

	// Exit successfully
	os.Exit(0)
}
